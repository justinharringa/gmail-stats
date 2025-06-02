from typing import List, Optional
from .thread import GmailThread


class GmailSender:
    """Represents a Gmail sender with their associated email threads.

    Attributes:
        sender: The sender's email address or name
        threads: List of GmailThread objects associated with this sender
    """

    def __init__(self, sender: str):
        """Initialize a new GmailSender.

        Args:
            sender: The sender's email address or name
        """
        self.sender = sender
        self.threads = []
        self._message_count = 0

    @property
    def message_count(self) -> int:
        """Get the total number of messages from this sender."""
        return self._message_count

    def add_thread(self, thread) -> None:
        """Add a thread to this sender's threads."""
        self.threads.append(thread)
        self._message_count += 1

    def add_threads(self, threads) -> None:
        """Add multiple threads to this sender's threads."""
        self.threads.extend(threads)
        self._message_count += len(threads)

    def num_threads(self) -> int:
        """Get the number of threads associated with this sender.

        Returns:
            The number of threads
        """
        return len(self.threads)

    def get_email(self) -> str:
        """Extract the email address from the sender string.

        If the sender string is in the format "Name <email@example.com>",
        extracts just the email address. Otherwise returns the original string.

        Returns:
            The sender's email address
        """
        if self.sender and "<" not in self.sender:
            return self.sender
        return self.sender.split("<")[1].split(">")[0]

    def __str__(self) -> str:
        """String representation of the sender."""
        return self.sender

    def __repr__(self) -> str:
        """String representation of the sender."""
        return self.sender
