# gmail-stats

## Usage
If you want to simply play around with this, you can run:

```
pipenv install
pipenv shell
python
```

Then you'll have a python shell where you can run:

```
import gmail
gmail_senders, gmail_sender_threads = get_sender_counts()
list(gmail_senders.items())[5:15]
```

You'll then be able to manipulate `gmail_senders` which is an `OrderedDict` of `GmailSenders`, and `gmail_sender_threads` which are the senders' `GmailThreads`.
