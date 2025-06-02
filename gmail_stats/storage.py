import shelve
import os
import logging
import json
import zlib
from typing import Dict, Optional, Tuple
from collections import OrderedDict
from datetime import datetime, timedelta

from .sender import GmailSender
from .thread import GmailThread

logger = logging.getLogger(__name__)

class GmailStorage:
    """Handles persistence of Gmail data using shelve with compression.
    
    Attributes:
        db_path: Path to the shelve database file
        last_sync: Timestamp of the last successful sync
        cache_duration: How long to keep cached data (default: 24 hours)
    """
    
    def __init__(self, db_path: str = '.env/gmail_data', cache_duration: int = 24):
        """Initialize GmailStorage.
        
        Args:
            db_path: Path to the shelve database file
            cache_duration: How long to keep cached data in hours
        """
        self.db_path = db_path
        self.cache_duration = timedelta(hours=cache_duration)
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
    def _compress_data(self, data: dict) -> bytes:
        """Compress data using zlib.
        
        Args:
            data: Dictionary to compress
            
        Returns:
            Compressed data as bytes
        """
        return zlib.compress(json.dumps(data).encode())
        
    def _decompress_data(self, data: bytes) -> dict:
        """Decompress data using zlib.
        
        Args:
            data: Compressed data as bytes
            
        Returns:
            Decompressed dictionary
        """
        return json.loads(zlib.decompress(data).decode())
        
    def _is_cache_valid(self, last_sync: str) -> bool:
        """Check if cached data is still valid.
        
        Args:
            last_sync: ISO format timestamp of last sync
            
        Returns:
            True if cache is valid, False otherwise
        """
        if not last_sync:
            return False
            
        last_sync_time = datetime.fromisoformat(last_sync)
        return datetime.now() - last_sync_time < self.cache_duration
        
    def save_data(self, 
                 senders: OrderedDict, 
                 sender_threads: Dict[str, GmailSender],
                 last_thread_id: str) -> None:
        """Save Gmail data to the database with compression.
        
        Args:
            senders: OrderedDict of sender email addresses and their message counts
            sender_threads: Dict of GmailSender objects keyed by sender email
            last_thread_id: ID of the last processed thread
        """
        try:
            with shelve.open(self.db_path) as db:
                # Convert GmailSender objects to dictionaries
                sender_threads_dict = {
                    email: {
                        'sender': sender.sender,
                        'threads': [
                            {
                                'thread_id': t.thread_id,
                                'labels': t.labels,
                                'sender': t.sender,
                                'subject': t.subject
                            }
                            for t in sender.threads
                        ]
                    }
                    for email, sender in sender_threads.items()
                }
                
                # Compress data before saving
                data = {
                    'senders': dict(senders),
                    'sender_threads': sender_threads_dict,
                    'last_thread_id': last_thread_id,
                    'last_sync': datetime.now().isoformat()
                }
                
                compressed_data = self._compress_data(data)
                db['data'] = compressed_data
                
            logger.info(f'Successfully saved compressed data to {self.db_path}')
        except Exception as e:
            logger.error(f'Error saving data: {str(e)}')
            raise
            
    def load_data(self) -> Tuple[Optional[OrderedDict], Optional[Dict[str, GmailSender]], Optional[str]]:
        """Load Gmail data from the database with decompression.
        
        Returns:
            Tuple containing:
            - OrderedDict of sender email addresses and their message counts
            - Dict of GmailSender objects keyed by sender email
            - ID of the last processed thread
        """
        try:
            with shelve.open(self.db_path) as db:
                if not db or 'data' not in db:
                    logger.info('No existing data found')
                    return None, None, None
                    
                # Decompress data
                compressed_data = db['data']
                data = self._decompress_data(compressed_data)
                
                # Check if cache is still valid
                if not self._is_cache_valid(data.get('last_sync')):
                    logger.info('Cache expired, will fetch fresh data')
                    return None, None, None
                
                senders = OrderedDict(data.get('senders', {}))
                sender_threads_dict = data.get('sender_threads', {})
                last_thread_id = data.get('last_thread_id')
                last_sync = data.get('last_sync')
                
                if last_sync:
                    logger.info(f'Last sync: {last_sync}')
                
                # Convert dictionaries back to GmailSender objects
                sender_threads = {}
                for email, sender_data in sender_threads_dict.items():
                    sender = GmailSender(sender_data['sender'])
                    for thread_data in sender_data['threads']:
                        thread = GmailThread(
                            thread_id=thread_data['thread_id'],
                            labels=thread_data['labels'],
                            sender=thread_data['sender'],
                            subject=thread_data['subject']
                        )
                        sender.add_thread(thread)
                    sender_threads[email] = sender
                
                return senders, sender_threads, last_thread_id
                
        except Exception as e:
            logger.error(f'Error loading data: {str(e)}')
            return None, None, None
            
    def clear_cache(self) -> None:
        """Clear all cached data."""
        try:
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
                logger.info('Cache cleared successfully')
        except Exception as e:
            logger.error(f'Error clearing cache: {str(e)}')
            raise 