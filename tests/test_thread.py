import pytest
from gmail_stats.thread import GmailThread

def test_gmail_thread_creation():
    """Test GmailThread creation with valid data."""
    thread = GmailThread(
        thread_id="123",
        labels=["INBOX", "UNREAD"],
        sender="test@example.com",
        subject="Test Subject"
    )
    
    assert thread.thread_id == "123"
    assert thread.labels == ["INBOX", "UNREAD"]
    assert thread.sender == "test@example.com"
    assert thread.subject == "Test Subject"

def test_gmail_thread_repr():
    """Test GmailThread string representation."""
    thread = GmailThread(
        thread_id="123",
        labels=["INBOX"],
        sender="test@example.com",
        subject="Test Subject"
    )
    
    assert str(thread) == "123 - Test Subject"
    assert repr(thread) == "123 - Test Subject"

def test_gmail_thread_empty_subject():
    """Test GmailThread with empty subject."""
    thread = GmailThread(
        thread_id="123",
        labels=["INBOX"],
        sender="test@example.com",
        subject=""
    )
    
    assert str(thread) == "123 - "

def test_gmail_thread_no_labels():
    """Test GmailThread with no labels."""
    thread = GmailThread(
        thread_id="123",
        labels=[],
        sender="test@example.com",
        subject="Test Subject"
    )
    
    assert thread.labels == [] 