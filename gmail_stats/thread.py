from typing import List


class GmailThread:
    """Represents a Gmail thread with its metadata.
    
    Attributes:
        thread_id: The unique identifier for the thread
        labels: List of labels applied to the thread
        sender: The sender's email address
        subject: The subject line of the thread
    """
    
    def __init__(self, thread_id: str, labels: List[str], sender: str, subject: str):
        """Initialize a new GmailThread.
        
        Args:
            thread_id: The unique identifier for the thread
            labels: List of labels applied to the thread
            sender: The sender's email address
            subject: The subject line of the thread
        """
        self.thread_id = thread_id
        self.labels = labels
        self.sender = sender
        self.subject = subject

    def __repr__(self) -> str:
        """Get a string representation of the GmailThread.
        
        Returns:
            A string in the format "thread_id - subject"
        """
        return f'{self.thread_id} - {self.subject}' 