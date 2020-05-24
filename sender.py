class GmailSender:
    def __init__(self, sender):
        self.sender = sender
        self.threads = []

    def add_thread(self, gmail_thread):
        self.threads.append(gmail_thread)

    def add_threads(self, gmail_threads):
        self.threads.extend(gmail_threads)

    def num_threads(self):
        return len(self.threads)

    def get_email(self):
        if self.sender and '<' not in self.sender:
            return self.sender
        return self.sender.split('<')[1].split('>')[0]

    def __repr__(self):
        return f'{self.sender} - {self.num_threads()} threads'
