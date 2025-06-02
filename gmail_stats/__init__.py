from __future__ import print_function
import pickle
import os.path
import logging
import time
import socket
from collections import OrderedDict
from operator import itemgetter
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
import ssl
from urllib3.exceptions import SSLError
from googleapiclient.errors import HttpError
import threading
from datetime import datetime, timedelta
import random
from limits import RateLimitItemPerSecond
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter
import signal
import sys
import atexit
import weakref
from googleapiclient.http import build_http
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import AuthorizedSession
import httplib2

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient import errors
from google.auth.exceptions import RefreshError

from .sender import GmailSender
from .thread import GmailThread
from .storage import GmailStorage
# 2 effective ways to give your program access:
# 1. Easiest but generates an app called Quickstart: https://developers.google.com/gmail/api/quickstart/python
# 1. Create a project by going to:
#    https://console.developers.google.com/projectcreate
# 2. Enable the Gmail APIs in your new project:
#    NOTE: make sure your new project name is selected in the top left
#    https://console.developers.google.com/apis
#    Search for Gmail, select it, then click Enable
# 3. Oauth consent screen: https://console.developers.google.com/apis/credentials/consent
# 3. Create credentials:
#    You'll see a button saying Create Credentials. Click that,
#    Which API are you using? Gmail API
#    Where will you be calling the API from? Other UI (e.g. Windows, CLI Tool)
#    What data will you be accessing? User data


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Paths for credentials and token files
CREDENTIALS_PATH = os.path.join('.env', 'credentials.json')
TOKEN_PATH = os.path.join('.env', 'token.pickle')

# Export the main classes and functions
__all__ = ['GmailThread', 'GmailSender', 'get_sender_counts']


class GmailThread:
    def __init__(self, thread_id: str, labels: List[str], sender: str, subject: str):
        self.thread_id = thread_id
        self.labels = labels
        self.sender = sender
        self.subject = subject

    def __repr__(self) -> str:
        return f'{self.thread_id} - {self.subject}'


# Create a global rate limiter using the limits library
# Gmail API allows 250 quota units per second per user
# We'll use 200 to be safe
rate_limiter = MovingWindowRateLimiter(MemoryStorage())
rate_limit = RateLimitItemPerSecond(200)  # 200 requests per second

# Global flag for graceful shutdown
shutdown_event = threading.Event()
# Global thread pool for cleanup
thread_pool = None

def cleanup_resources():
    """Cleanup function to be called on exit."""
    global thread_pool
    if thread_pool is not None:
        logger.debug("Cleaning up thread pool...")
        thread_pool.shutdown(wait=False)
        thread_pool = None

# Register cleanup function
atexit.register(cleanup_resources)

def signal_handler(signum, frame):
    """Handle interrupt signals for graceful shutdown."""
    if shutdown_event.is_set():
        logger.info("\nForce quitting...")
        sys.exit(1)
        
    logger.info("\nReceived interrupt signal. Shutting down gracefully...")
    shutdown_event.set()
    
    # Give threads a chance to clean up
    time.sleep(1)
    
    if thread_pool is not None:
        logger.info("Shutting down thread pool...")
        thread_pool.shutdown(wait=False)
    
    logger.info("Shutdown complete.")
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def process_single_thread(service, thread, user_id: str = 'me', max_retries: int = 3) -> Optional[dict]:
    """Process a single thread with retry logic and rate limiting.
    
    Args:
        service: Authorized Gmail API service instance
        thread: Thread object to process
        user_id: User's email address or 'me'
        max_retries: Maximum number of retry attempts
        
    Returns:
        Dictionary with thread data or None if processing failed
    """
    thread_id = thread['id']
    retry_count = 0
    last_error = None
    
    while retry_count < max_retries and not shutdown_event.is_set():
        try:
            # Wait for rate limiter before making API call
            if not rate_limiter.hit(rate_limit):
                time.sleep(0.1)  # Small delay if we hit the rate limit
                continue
            
            # Execute the request
            thread_data = service.users().threads().get(
                userId=user_id,
                id=thread_id
            ).execute()
            
            if not thread_data or not thread_data.get('messages'):
                return None
                
            first_message = thread_data['messages'][0]
            if not first_message or not isinstance(first_message, dict):
                return None
                
            label_ids = first_message.get('labelIds', [])
            if not isinstance(label_ids, list):
                return None
            
            if 'UNREAD' not in label_ids:
                return None
                
            sender = get_sender(first_message)
            subject = get_subject(first_message)
            
            if not sender:
                logger.debug(f'No sender found for thread {thread_id}')
                return None
                
            return {
                'sender': sender,
                'thread': GmailThread(thread_id, label_ids, sender, subject)
            }
            
        except (SSLError, ssl.SSLError) as e:
            last_error = e
            logger.debug(f'SSL error processing thread {thread_id} (attempt {retry_count + 1}/{max_retries}): {str(e)}')
            # Longer delay for SSL errors
            time.sleep(5 * (2 ** retry_count))  # Exponential backoff with longer base delay
            
        except (HttpError, errors.HttpError) as e:
            if hasattr(e, 'resp') and e.resp.status == 429:  # Rate limit exceeded
                last_error = e
                logger.debug(f'Rate limit exceeded for thread {thread_id} (attempt {retry_count + 1}/{max_retries})')
                # Exponential backoff with jitter
                sleep_time = (2 ** retry_count) + (random.random() * 0.1)
                time.sleep(sleep_time)
            elif hasattr(e, 'resp') and e.resp.status in [500, 502, 503, 504]:  # Server errors
                last_error = e
                logger.debug(f'Server error processing thread {thread_id} (attempt {retry_count + 1}/{max_retries}): {str(e)}')
                time.sleep(2 ** retry_count)  # Exponential backoff
            else:
                logger.error(f'HTTP error processing thread {thread_id}: {str(e)}')
                return None
                
        except (TimeoutError, socket.timeout) as e:
            last_error = e
            logger.debug(f'Timeout processing thread {thread_id} (attempt {retry_count + 1}/{max_retries})')
            time.sleep(2 ** retry_count)  # Exponential backoff
            
        except (AttributeError, TypeError) as e:
            last_error = e
            logger.debug(f'Data error processing thread {thread_id} (attempt {retry_count + 1}/{max_retries}): {str(e)}')
            time.sleep(1)  # Short delay for data errors
            
        except Exception as e:
            last_error = e
            logger.error(f'Unexpected error processing thread {thread_id}: {str(e)}')
            return None
            
        retry_count += 1
    
    if last_error and not shutdown_event.is_set():
        # Only log the final error at WARNING level if all retries failed
        if isinstance(last_error, (SSLError, ssl.SSLError)):
            logger.warning(f'Failed to process thread {thread_id} after {max_retries} attempts due to SSL errors')
        elif isinstance(last_error, (HttpError, errors.HttpError)) and hasattr(last_error, 'resp') and last_error.resp.status in [429, 500, 502, 503, 504]:
            logger.warning(f'Failed to process thread {thread_id} after {max_retries} attempts due to server errors')
        elif isinstance(last_error, (TimeoutError, socket.timeout)):
            logger.warning(f'Failed to process thread {thread_id} after {max_retries} attempts due to timeouts')
        else:
            logger.error(f'Failed to process thread {thread_id} after {max_retries} attempts: {str(last_error)}')
    return None


def process_thread_batch(service, threads: List[dict], user_id: str = 'me') -> Tuple[Dict[str, int], Dict[str, GmailSender]]:
    """Process a batch of threads in parallel with rate limiting.
    
    Args:
        service: Authorized Gmail API service instance
        threads: List of thread objects to process
        user_id: User's email address or 'me'
        
    Returns:
        Tuple containing:
        - Dict of sender email addresses and their message counts
        - Dict of GmailSender objects keyed by sender email
    """
    global thread_pool
    senders = {}
    sender_threads = {}
    
    # Create a new thread pool for each batch with reduced workers
    thread_pool = ThreadPoolExecutor(max_workers=1)  # Reduced to 1 worker to prevent memory issues
    try:
        # Process threads in smaller sub-batches to prevent memory issues
        sub_batch_size = 5  # Reduced from 10 to 5
        for i in range(0, len(threads), sub_batch_size):
            if shutdown_event.is_set():
                logger.info("Shutdown requested, stopping batch processing...")
                break
                
            sub_batch = threads[i:i + sub_batch_size]
            futures = [thread_pool.submit(process_single_thread, service, thread, user_id) for thread in sub_batch]
            
            for future in as_completed(futures):
                if shutdown_event.is_set():
                    logger.info("Shutdown requested, cancelling remaining tasks...")
                    for f in futures:
                        f.cancel()
                    break
                    
                try:
                    result = future.result(timeout=30)  # Add timeout to prevent hanging
                    if result:
                        sender = result['sender']
                        thread = result['thread']
                        
                        senders[sender] = senders.get(sender, 0) + 1
                        
                        if sender in sender_threads:
                            sender_threads[sender].add_thread(thread)
                        else:
                            gmail_sender = GmailSender(sender)
                            gmail_sender.add_thread(thread)
                            sender_threads[sender] = gmail_sender
                except TimeoutError:
                    logger.warning("Thread processing timed out, skipping...")
                    continue
                except Exception as e:
                    logger.debug(f'Error processing thread result: {str(e)}')
                    continue
                    
            # Longer delay between sub-batches to prevent memory buildup
            time.sleep(0.5)
            
            if shutdown_event.is_set():
                break
                
    finally:
        # Ensure thread pool is properly shut down
        if thread_pool is not None:
            thread_pool.shutdown(wait=False)
            thread_pool = None
    
    return senders, sender_threads


def show_unread_inbox_threads(service, threads: List[dict], user_id: str = 'me') -> Tuple[Dict[str, int], Dict[str, GmailSender]]:
    """Process unread inbox threads and count messages by sender.
    
    Args:
        service: Authorized Gmail API service instance
        threads: List of thread objects to process
        user_id: User's email address or 'me'
        
    Returns:
        Tuple containing:
        - Dict of sender email addresses and their message counts
        - Dict of GmailSender objects keyed by sender email
    """
    # Process threads in smaller batches
    batch_size = 50  # Reduced from 100 to 50
    total_senders = {}
    total_sender_threads = {}
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("[cyan]{task.completed}/{task.total} threads"),
        TimeElapsedColumn(),
    ) as progress:
        task = progress.add_task(
            "[cyan]Processing threads...",
            total=len(threads),
            completed=0
        )
        
        try:
            for i in range(0, len(threads), batch_size):
                if shutdown_event.is_set():
                    logger.info("Shutdown requested, stopping thread processing...")
                    break
                    
                batch = threads[i:i + batch_size]
                senders, sender_threads = process_thread_batch(service, batch, user_id)
                
                # Merge results
                for sender, count in senders.items():
                    total_senders[sender] = total_senders.get(sender, 0) + count
                    if sender in sender_threads:
                        if sender in total_sender_threads:
                            total_sender_threads[sender].add_threads(sender_threads[sender].threads)
                        else:
                            total_sender_threads[sender] = sender_threads[sender]
                
                progress.update(task, advance=len(batch))
                
                # Small delay between batches to prevent memory buildup
                time.sleep(0.2)
                
                if shutdown_event.is_set():
                    break
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, initiating shutdown...")
            shutdown_event.set()
            raise
    
    return total_senders, total_sender_threads


def get_sender_counts() -> Tuple[Optional[OrderedDict], Optional[Dict[str, GmailSender]]]:
    """Get counts of unread emails by sender and their associated threads.
    
    Returns:
        Tuple containing:
        - OrderedDict of sender email addresses and their message counts
        - Dict of GmailSender objects keyed by sender email
    """
    storage = GmailStorage()
    cached_senders, cached_sender_threads, last_thread_id = storage.load_data()
    
    try:
        service = get_gmail_service()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
        ) as progress:
            progress.add_task("[cyan]Fetching thread list...", total=None)
            threads = list_threads_with_labels(service, 'me', ['INBOX'])
        
        if not threads:
            logger.info('No threads found in inbox')
            return cached_senders, cached_sender_threads
            
        logger.info(f'Processing {len(threads)} threads...')
        
        # If we have cached data, only process new threads
        if last_thread_id and cached_senders and cached_sender_threads:
            # Create a set of cached thread IDs for faster lookup
            cached_thread_ids = set()
            for sender in cached_sender_threads.values():
                for thread in sender.threads:
                    cached_thread_ids.add(thread.thread_id)
            
            # Find new threads that aren't in our cache
            new_threads = []
            for thread in threads:
                if thread['id'] not in cached_thread_ids:
                    new_threads.append(thread)
            
            if new_threads:
                logger.info(f'Found {len(new_threads)} new threads since last sync')
                new_senders, new_sender_threads = show_unread_inbox_threads(service, new_threads)
                
                # Merge new data with cached data
                for sender, count in new_senders.items():
                    cached_senders[sender] = cached_senders.get(sender, 0) + count
                    if sender in new_sender_threads:
                        if sender in cached_sender_threads:
                            cached_sender_threads[sender].add_threads(new_sender_threads[sender].threads)
                        else:
                            cached_sender_threads[sender] = new_sender_threads[sender]
                
                # Sort senders by count
                sorted_senders = OrderedDict(sorted(cached_senders.items(), key=itemgetter(1), reverse=True))
                
                # Save updated data
                if new_threads:
                    storage.save_data(sorted_senders, cached_sender_threads, new_threads[0]['id'])
                
                return sorted_senders, cached_sender_threads
            else:
                logger.info('No new threads since last sync')
                return cached_senders, cached_sender_threads
        
        # If no cached data or first run, process all threads
        senders, sender_threads = show_unread_inbox_threads(service, threads)
        sorted_senders = OrderedDict(sorted(senders.items(), key=itemgetter(1), reverse=True))
        
        # Save data
        if threads:
            storage.save_data(sorted_senders, sender_threads, threads[0]['id'])
        
        return sorted_senders, sender_threads
        
    except Exception as e:
        logger.error(f'Error getting sender counts: {str(e)}')
        # If there's an error, return cached data if available
        if cached_senders and cached_sender_threads:
            logger.info('Returning cached data due to error')
            return cached_senders, cached_sender_threads
        raise


def get_gmail_service():
    """Get an authorized Gmail API service instance.
    
    Returns:
        Authorized Gmail API service instance.
        
    Raises:
        FileNotFoundError: If credentials.json is not found
        RefreshError: If token refresh fails
    """
    creds = None
    
    # Check if token exists
    if os.path.exists(TOKEN_PATH):
        try:
            with open(TOKEN_PATH, 'rb') as token:
                creds = pickle.load(token)
        except Exception as e:
            logger.error(f'Error loading token.pickle: {str(e)}')
            # If token is corrupted, remove it
            os.remove(TOKEN_PATH)
            logger.info('Removed corrupted token.pickle')

    # If no valid credentials exist, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError as e:
                logger.error(f'Token refresh failed: {str(e)}')
                logger.info('Removing expired token.pickle')
                os.remove(TOKEN_PATH)
                raise
            except Exception as e:
                logger.error(f'Error refreshing credentials: {str(e)}')
                raise
        else:
            try:
                if not os.path.exists(CREDENTIALS_PATH):
                    raise FileNotFoundError(
                        f'Credentials file not found at {CREDENTIALS_PATH}. '
                        'Please place your credentials.json file in the .env directory.'
                    )
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
                creds = flow.run_local_server(port=0)
            except Exception as e:
                logger.error(f'Error running auth flow: {str(e)}')
                raise

        try:
            # Ensure .env directory exists
            os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
            with open(TOKEN_PATH, 'wb') as token:
                pickle.dump(creds, token)
            logger.info('Saved new token to token.pickle')
        except Exception as e:
            logger.error(f'Error saving credentials: {str(e)}')
            raise

    try:
        # Build the service with credentials directly
        # The Google API client will handle SSL and HTTP configuration internally
        service = build('gmail', 'v1', credentials=creds, cache_discovery=False)
        return service
    except Exception as e:
        logger.error(f'Error building Gmail service: {str(e)}')
        raise


def list_threads_with_labels(service, user_id: str, label_ids: List[str] = None) -> List[dict]:
    """List all Threads of the user's mailbox with label_ids applied.
    
    Args:
        service: Authorized Gmail API service instance
        user_id: User's email address or 'me'
        label_ids: Only return Threads with these labelIds applied
        
    Returns:
        List of threads that match the criteria of the query
    """
    if label_ids is None:
        label_ids = []
        
    try:
        response = service.users().threads().list(userId=user_id, labelIds=label_ids).execute()
        threads = []
        
        if 'threads' in response:
            threads.extend(response['threads'])
            logger.debug(f'Got first page of threads')

        while 'nextPageToken' in response:
            page_token = response['nextPageToken']
            logger.debug(f'Getting threads with nextPageToken: {page_token}')
            response = service.users().threads().list(
                userId=user_id,
                labelIds=label_ids,
                pageToken=page_token
            ).execute()
            threads.extend(response['threads'])

        return threads
        
    except errors.HttpError as error:
        logger.error(f'An error occurred while listing threads: {error}')
        raise


def get_sender(message: dict) -> Optional[str]:
    """Extract sender email from message headers.
    
    Args:
        message: Gmail message object
        
    Returns:
        Sender email address or None if not found
    """
    for header in message['payload']['headers']:
        if header['name'] and header['name'].lower() == 'from':
            return header['value']
    return None


def get_subject(message: dict) -> Optional[str]:
    """Extract subject from message headers.
    
    Args:
        message: Gmail message object
        
    Returns:
        Subject line or None if not found
    """
    for header in message['payload']['headers']:
        if header['name'] and header['name'].lower() == 'subject':
            return header['value']
    return None
