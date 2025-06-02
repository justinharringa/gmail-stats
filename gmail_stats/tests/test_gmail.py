import unittest
from unittest.mock import Mock, patch
from gmail_stats import GmailThread, get_sender, get_subject
from gmail_stats.sender import GmailSender


class TestGmailThread(unittest.TestCase):
    def test_gmail_thread_creation(self):
        thread = GmailThread("123", ["INBOX"], "test@example.com", "Test Subject")
        self.assertEqual(thread.thread_id, "123")
        self.assertEqual(thread.labels, ["INBOX"])
        self.assertEqual(thread.sender, "test@example.com")
        self.assertEqual(thread.subject, "Test Subject")

    def test_gmail_thread_repr(self):
        thread = GmailThread("123", ["INBOX"], "test@example.com", "Test Subject")
        expected_repr = "123 - Test Subject"
        self.assertEqual(repr(thread), expected_repr)


class TestGmailSender(unittest.TestCase):
    def setUp(self):
        self.sender = GmailSender("test@example.com")

    def test_sender_creation(self):
        self.assertEqual(self.sender.sender, "test@example.com")
        self.assertEqual(self.sender.threads, [])

    def test_add_thread(self):
        thread = GmailThread("123", ["INBOX"], "test@example.com", "Test Subject")
        self.sender.add_thread(thread)
        self.assertEqual(len(self.sender.threads), 1)
        self.assertEqual(self.sender.threads[0], thread)

    def test_add_threads(self):
        threads = [
            GmailThread("123", ["INBOX"], "test@example.com", "Test Subject 1"),
            GmailThread("124", ["INBOX"], "test@example.com", "Test Subject 2"),
        ]
        self.sender.add_threads(threads)
        self.assertEqual(len(self.sender.threads), 2)

    def test_num_threads(self):
        self.assertEqual(self.sender.num_threads(), 0)
        thread = GmailThread("123", ["INBOX"], "test@example.com", "Test Subject")
        self.sender.add_thread(thread)
        self.assertEqual(self.sender.num_threads(), 1)

    def test_get_email_simple(self):
        sender = GmailSender("test@example.com")
        self.assertEqual(sender.get_email(), "test@example.com")

    def test_get_email_complex(self):
        sender = GmailSender("Test User <test@example.com>")
        self.assertEqual(sender.get_email(), "test@example.com")


class TestMessageHelpers(unittest.TestCase):
    def test_get_sender(self):
        message = {
            "payload": {
                "headers": [
                    {"name": "From", "value": "test@example.com"},
                    {"name": "Subject", "value": "Test Subject"},
                ]
            }
        }
        self.assertEqual(get_sender(message), "test@example.com")

    def test_get_subject(self):
        message = {
            "payload": {
                "headers": [
                    {"name": "From", "value": "test@example.com"},
                    {"name": "Subject", "value": "Test Subject"},
                ]
            }
        }
        self.assertEqual(get_subject(message), "Test Subject")

    def test_get_sender_not_found(self):
        message = {
            "payload": {"headers": [{"name": "Subject", "value": "Test Subject"}]}
        }
        self.assertIsNone(get_sender(message))

    def test_get_subject_not_found(self):
        message = {
            "payload": {"headers": [{"name": "From", "value": "test@example.com"}]}
        }
        self.assertIsNone(get_subject(message))


if __name__ == "__main__":
    unittest.main()
