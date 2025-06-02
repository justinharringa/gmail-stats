import pytest
from click.testing import CliRunner
from gmail_stats.cli import cli, display_sender_table, display_sender_details
from gmail_stats.sender import GmailSender
from gmail_stats.thread import GmailThread
from collections import OrderedDict

@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()

@pytest.fixture
def sample_senders():
    """Create sample sender data."""
    senders = OrderedDict([
        ("test1@example.com", GmailSender("test1@example.com")),
        ("test2@example.com", GmailSender("test2@example.com"))
    ])
    
    # Add threads to senders
    thread1 = GmailThread("123", ["INBOX", "UNREAD"], "test1@example.com", "Subject 1")
    thread2 = GmailThread("456", ["INBOX"], "test1@example.com", "Subject 2")
    thread3 = GmailThread("789", ["INBOX", "UNREAD"], "test2@example.com", "Subject 3")
    
    senders["test1@example.com"].add_threads([thread1, thread2])
    senders["test2@example.com"].add_thread(thread3)
    
    return senders

def test_list_command(runner, mocker):
    """Test the list command."""
    # Create sample data
    sender1 = GmailSender("test1@example.com")
    sender2 = GmailSender("test2@example.com")
    
    # Add threads to senders
    thread1 = GmailThread("123", ["INBOX", "UNREAD"], "test1@example.com", "Subject 1")
    thread2 = GmailThread("456", ["INBOX"], "test1@example.com", "Subject 2")
    thread3 = GmailThread("789", ["INBOX", "UNREAD"], "test2@example.com", "Subject 3")
    
    sender1.add_threads([thread1, thread2])
    sender2.add_thread(thread3)
    
    # Mock get_sender_counts to return sample data
    mocker.patch('gmail_stats.cli.get_sender_counts', return_value=(
        OrderedDict([("test1@example.com", 2), ("test2@example.com", 1)]),
        {"test1@example.com": sender1, "test2@example.com": sender2}
    ))
    
    result = runner.invoke(cli, ['list'])
    assert result.exit_code == 0
    assert "test1@example.com" in result.output
    assert "test2@example.com" in result.output

def test_show_command(runner, mocker):
    """Test the show command."""
    # Mock get_sender_counts to return sample data
    sender = GmailSender("test@example.com")
    thread = GmailThread("123", ["INBOX", "UNREAD"], "test@example.com", "Test Subject")
    sender.add_thread(thread)
    
    mocker.patch('gmail_stats.cli.get_sender_counts', return_value=(
        OrderedDict([("test@example.com", 1)]),
        {"test@example.com": sender}
    ))
    
    result = runner.invoke(cli, ['show', 'test@example.com'])
    assert result.exit_code == 0
    assert "test@example.com" in result.output
    assert "Test Subject" in result.output

def test_interactive_command(runner, mocker):
    """Test the interactive command."""
    # Mock get_sender_counts to return sample data
    sender = GmailSender("test@example.com")
    thread = GmailThread("123", ["INBOX", "UNREAD"], "test@example.com", "Test Subject")
    sender.add_thread(thread)
    
    mocker.patch('gmail_stats.cli.get_sender_counts', return_value=(
        OrderedDict([("test@example.com", 1)]),
        {"test@example.com": sender}
    ))
    
    # Mock click.prompt to simulate user input
    mocker.patch('click.prompt', return_value='q')
    
    result = runner.invoke(cli, ['interactive'])
    assert result.exit_code == 0
    assert "test@example.com" in result.output

def test_display_sender_table(sample_senders):
    """Test the display_sender_table function."""
    # This is a visual test, we just check it doesn't raise exceptions
    display_sender_table(sample_senders, 'messages')
    display_sender_table(sample_senders, 'threads')
    display_sender_table(sample_senders, 'unread_threads')

def test_display_sender_details(sample_senders):
    """Test the display_sender_details function."""
    # This is a visual test, we just check it doesn't raise exceptions
    display_sender_details(sample_senders["test1@example.com"]) 