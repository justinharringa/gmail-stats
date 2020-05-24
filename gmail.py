from __future__ import print_function
import pickle
import os.path
from sender import GmailSender
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient import errors
from collections import OrderedDict
from operator import itemgetter

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


# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


class GmailThread:
    def __init__(self, thread_id, labels, sender, subject):
        self.thread_id = thread_id
        self.labels = labels
        self.sender = sender
        self.subject = subject

    def __repr__(self):
        return f'{self.thread_id} - {self.subject}'


def get_sender_counts():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    service = get_gmail_service()

    # Call the Gmail API
    threads = list_threads_with_labels(service, 'me', ['INBOX'])
    sorted_senders = None
    sender_threads = None
    if threads:
        print(f'Processing {len(threads)} threads...')
        senders, sender_threads = show_unread_inbox_threads(service, threads)
        sorted_senders = OrderedDict(sorted(senders.items(), key=itemgetter(1), reverse=True))
    return sorted_senders, sender_threads
    # results = service.users().labels().list(userId='me').execute()
    # labels = results.get('labels', [])
    #
    # if not labels:
    #     print('No labels found.')
    # else:
    #     print('Labels:')
    #     for label in labels:
    #         print(label['name'])


def get_gmail_service():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    service = build('gmail', 'v1', credentials=creds)
    return service


def show_unread_inbox_threads(service, threads, user_id='me'):
    senders = {}
    sender_threads = {}
    for thread in threads:
        thread_id = thread['id']
        thread_data = service.users().threads().get(userId=user_id, id=thread_id).execute()
        nmsgs = len(thread_data['messages'])

        first_message = thread_data['messages'][0]
        label_ids = first_message['labelIds']
        if 'UNREAD' in label_ids:
            print('Thread: {}'.format(thread_id))
            print('Labels: {}'.format(label_ids))
            sender = get_sender(first_message)
            print('Sender: {}'.format(sender))
            subject = get_subject(first_message)

            if sender in senders:
                senders[sender] += 1
            else:
                senders[sender] = 1

            gmail_thread = GmailThread(thread_id, label_ids, sender, subject)
            if sender in sender_threads:
                sender_threads[sender].add_thread(gmail_thread)
            else:
                gmail_sender = GmailSender(sender)
                gmail_sender.add_thread(gmail_thread)
                sender_threads[sender] = gmail_sender
            # if nmsgs > 2:  # skip if <3 msgs in thread
            #     msg = first_message['payload']
            #     subject = ''
            #     for header in msg['headers']:
            #         if header['name'] == 'Subject':
            #             subject = header['value']
            #             break
            #     if subject:  # skip if no Subject line
            #         print('- %s (%d msgs)' % (subject, nmsgs))
    return senders, sender_threads


def list_threads_with_labels(service, user_id, label_ids=[]):
    """List all Threads of the user's mailbox with label_ids applied.

  Args:
    service: Authorized Gmail API service instance.
    user_id: User's email address. The special value "me"
    can be used to indicate the authenticated user.
    label_ids: Only return Threads with these labelIds applied.

  Returns:
    List of threads that match the criteria of the query. Note that the returned
    list contains Thread IDs, you must use get with the appropriate
    ID to get the details for a Thread.
  """
    try:
        response = service.users().threads().list(userId=user_id,
                                                  labelIds=label_ids).execute()
        threads = []
        if 'threads' in response:
            threads.extend(response['threads'])
            print(f'Got first page of threads')

        while 'nextPageToken' in response:
            page_token = response['nextPageToken']
            print(f'Getting threads with nextPageToken: {page_token}')
            response = service.users().threads().list(userId=user_id,
                                                      labelIds=label_ids,
                                                      pageToken=page_token).execute()
            threads.extend(response['threads'])

        return threads
    except errors.HttpError as error:
        print(f'An error occurred: {error}')


def get_sender(message):
    for header in message['payload']['headers']:
        if header['name'] and header['name'].lower() == 'from':
            return header['value']
    return None


def get_subject(message):
    for header in message['payload']['headers']:
        if header['name'] and header['name'].lower() == 'subject':
            return header['value']
    return None


if __name__ == '__main__':
    gmail_senders, gmail_sender_threads = get_sender_counts()
