import os
import pytest
from collections import OrderedDict
from gmail_stats.storage import GmailStorage
from gmail_stats.sender import GmailSender
from gmail_stats.thread import GmailThread


@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary database path."""
    return str(tmp_path / "test_gmail_data")


@pytest.fixture
def sample_data():
    """Create sample data for testing."""
    senders = OrderedDict([("test1@example.com", 2), ("test2@example.com", 1)])

    sender_threads = {
        "test1@example.com": GmailSender("test1@example.com"),
        "test2@example.com": GmailSender("test2@example.com"),
    }

    # Add threads to senders
    thread1 = GmailThread("123", ["INBOX", "UNREAD"], "test1@example.com", "Subject 1")
    thread2 = GmailThread("456", ["INBOX"], "test1@example.com", "Subject 2")
    thread3 = GmailThread("789", ["INBOX", "UNREAD"], "test2@example.com", "Subject 3")

    sender_threads["test1@example.com"].add_threads([thread1, thread2])
    sender_threads["test2@example.com"].add_thread(thread3)

    return senders, sender_threads, "123"


def test_storage_creation(temp_db_path):
    """Test GmailStorage creation."""
    storage = GmailStorage(temp_db_path)
    assert storage.db_path == temp_db_path
    assert os.path.exists(os.path.dirname(temp_db_path))


def test_save_and_load_data(temp_db_path, sample_data):
    """Test saving and loading data."""
    senders, sender_threads, last_thread_id = sample_data
    storage = GmailStorage(temp_db_path)

    # Save data
    storage.save_data(senders, sender_threads, last_thread_id)

    # Load data
    loaded_senders, loaded_sender_threads, loaded_last_thread_id = storage.load_data()

    # Verify data
    assert dict(loaded_senders) == dict(senders)
    assert loaded_last_thread_id == last_thread_id

    # Verify sender threads
    for email, sender in loaded_sender_threads.items():
        assert email in sender_threads
        assert len(sender.threads) == len(sender_threads[email].threads)
        for t1, t2 in zip(sender.threads, sender_threads[email].threads):
            assert t1.thread_id == t2.thread_id
            assert t1.subject == t2.subject
            assert t1.labels == t2.labels


def test_load_empty_data(temp_db_path):
    """Test loading from empty database."""
    storage = GmailStorage(temp_db_path)
    senders, sender_threads, last_thread_id = storage.load_data()

    assert senders is None
    assert sender_threads is None
    assert last_thread_id is None


def test_save_data_error(temp_db_path, sample_data):
    """Test error handling when saving data."""
    senders, sender_threads, last_thread_id = sample_data
    storage = GmailStorage(temp_db_path)

    # Create a read-only directory
    os.chmod(os.path.dirname(temp_db_path), 0o444)

    with pytest.raises(Exception):
        storage.save_data(senders, sender_threads, last_thread_id)

    # Restore permissions
    os.chmod(os.path.dirname(temp_db_path), 0o755)
