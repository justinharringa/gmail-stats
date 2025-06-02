import pytest
from gmail_stats.sender import GmailSender
from gmail_stats.thread import GmailThread


def test_gmail_sender_creation():
    """Test GmailSender creation with valid data."""
    sender = GmailSender("test@example.com")

    assert sender.sender == "test@example.com"
    assert sender.threads == []
    assert sender.message_count == 0


def test_gmail_sender_add_thread():
    """Test adding a thread to GmailSender."""
    sender = GmailSender("test@example.com")
    thread = GmailThread(
        thread_id="123",
        labels=["INBOX", "UNREAD"],
        sender="test@example.com",
        subject="Test Subject",
    )

    sender.add_thread(thread)
    assert len(sender.threads) == 1
    assert sender.threads[0] == thread
    assert sender.message_count == 1


def test_gmail_sender_add_threads():
    """Test adding multiple threads to GmailSender."""
    sender = GmailSender("test@example.com")
    threads = [
        GmailThread(
            thread_id="123",
            labels=["INBOX", "UNREAD"],
            sender="test@example.com",
            subject="Test Subject 1",
        ),
        GmailThread(
            thread_id="456",
            labels=["INBOX"],
            sender="test@example.com",
            subject="Test Subject 2",
        ),
    ]

    sender.add_threads(threads)
    assert len(sender.threads) == 2
    assert sender.message_count == 2
    assert sender.threads[0].thread_id == "123"
    assert sender.threads[1].thread_id == "456"


def test_gmail_sender_repr():
    """Test GmailSender string representation."""
    sender = GmailSender("test@example.com")
    assert str(sender) == "test@example.com"
    assert repr(sender) == "test@example.com"


def test_gmail_sender_empty():
    """Test GmailSender with no threads."""
    sender = GmailSender("test@example.com")
    assert len(sender.threads) == 0
    assert sender.message_count == 0
