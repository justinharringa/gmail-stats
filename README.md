# Gmail Stats

A command-line tool to analyze your Gmail inbox, providing insights about your email senders and threads.

## Features

- View email statistics by sender
- Sort by message count, total threads, or unread threads
- Interactive exploration of your Gmail data
- Persistent storage of email data for faster subsequent runs
- Beautiful terminal interface with rich formatting
- Automatic token management and refresh
- Incremental updates (only processes new emails)
- Real-time progress indicators
- Parallel processing for faster data retrieval
- Data compression for efficient storage
- Batch processing of email threads

## Installation

1. Clone the repository:
```bash
git clone https://github.com/justinharringa/gmail-stats.git
cd gmail-stats
```

2. Install dependencies using Poetry:
```bash
poetry install
```

3. Set up Google API credentials:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Gmail API for your project
   - Create OAuth 2.0 credentials (Desktop application)
   - Download the credentials and save them as `.env/credentials.json`

## Usage

### List Senders

View all senders with their message and thread counts:

```bash
# Sort by message count (default)
poetry run gmail-stats list

# Sort by total threads
poetry run gmail-stats list --sort-by threads

# Sort by unread threads
poetry run gmail-stats list --sort-by unread_threads
```

### Show Sender Details

View detailed information about a specific sender:

```bash
poetry run gmail-stats show "example@email.com"
```

This will show:
- Total messages and threads
- Unread thread count
- List of all threads with their subjects and labels
- Read/unread status for each thread

### Interactive Mode

Start an interactive session to explore your Gmail data:

```bash
# Start with default sorting (by message count)
poetry run gmail-stats interactive

# Start with a specific sort order
poetry run gmail-stats interactive --sort-by threads
```

In interactive mode, you can:
1. View the sender list
2. Enter a sender's email to see their details
3. Press 's' to change the sort criteria
4. Press 'q' to quit

## Data Storage

The tool uses `shelve` to store email data locally in `.env/gmail_data`. This means:
- Subsequent runs are faster as they only process new emails
- Your data persists between runs
- You can analyze your email history even when offline
- Automatic token management and refresh
- Incremental updates (only processes new emails since last sync)
- Fallback to cached data if API calls fail
- Data compression to minimize storage space
- Configurable cache duration (default: 24 hours)

The storage system tracks:
- Sender information and message counts
- Thread details including subjects and labels
- Last processed thread ID for incremental updates
- Last sync timestamp
- Authentication tokens
- Compressed data for efficient storage

## Development

### Project Structure

```
gmail-stats/
├── gmail_stats/
│   ├── __init__.py      # Core functionality
│   ├── cli.py           # Command-line interface
│   ├── sender.py        # Sender-related classes
│   ├── thread.py        # Thread-related classes
│   └── storage.py       # Data persistence
├── tests/               # Test suite
│   ├── test_cli.py     # CLI tests
│   ├── test_sender.py  # Sender class tests
│   ├── test_storage.py # Storage tests
│   └── test_thread.py  # Thread class tests
├── pyproject.toml       # Project configuration
└── README.md           # This file
```

### Testing

The project uses pytest for testing and pytest-cov for coverage reporting. To run the tests:

```bash
# Run all tests
poetry run pytest

# Run tests with coverage report
poetry run pytest --cov=gmail_stats --cov-report=term-missing --cov-report=html
```

The coverage report will show:
- Overall code coverage percentage
- Line-by-line coverage information
- Missing lines in the code
- HTML report in the `htmlcov/` directory

Current test coverage includes:
- Unit tests for all classes (GmailThread, GmailSender, GmailStorage)
- CLI command tests with mocked Gmail API
- Storage persistence tests
- Visual display tests
- Error handling and edge cases

### Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

Please ensure:
- All tests pass (`poetry run pytest`)
- Code coverage is maintained or improved
- New features include appropriate tests
- Documentation is updated
- Error handling is implemented
- Logging is added for important operations

## License

This project is licensed under the MIT License - see the LICENSE file for details.
