# Chat Logging System

The Catmandu bot includes a comprehensive chat logging system that stores all chat interactions in daily log files for analysis and monitoring.

## Features

- **Daily Log Files**: Chat interactions are stored in separate files for each day (`YYYY-MM-DD.jsonl`)
- **Structured Logging**: Each interaction is logged as a JSON object with detailed metadata
- **User Information**: Captures participant names, user IDs, and other Telegram user data
- **Command Tracking**: Logs both regular messages and command executions with response metrics
- **Analysis Tools**: Built-in scripts and Makefile commands for analyzing chat data

## Log Format

Each log entry is stored as a JSON Lines (JSONL) format with the following structure:

```json
{
  "timestamp": "2024-01-15T10:30:00",
  "chat_id": 123,
  "participant_name": "@alice",
  "message_type": "message",
  "text_length": 12,
  "text_preview": "Hello world!",
  "user_id": 456,
  "is_bot": false,
  "language_code": "en"
}
```

### Command Log Entry Example

```json
{
  "timestamp": "2024-01-15T10:31:00",
  "chat_id": 123,
  "participant_name": "@alice",
  "message_type": "command",
  "text_length": 10,
  "text_preview": "/echo test",
  "user_id": 456,
  "is_bot": false,
  "command": "echo",
  "cattackle_name": "echo",
  "response_length": 25
}
```

## Log Fields

| Field              | Description                            | Type    | Always Present |
| ------------------ | -------------------------------------- | ------- | -------------- |
| `timestamp`        | ISO format timestamp                   | string  | ✓              |
| `chat_id`          | Telegram chat ID                       | number  | ✓              |
| `participant_name` | User display name or username          | string  | ✓              |
| `message_type`     | "message" or "command"                 | string  | ✓              |
| `text_length`      | Length of the message text             | number  | ✓              |
| `text_preview`     | First 100 characters of message        | string  | ✓              |
| `user_id`          | Telegram user ID                       | number  | ✓              |
| `is_bot`           | Whether user is a bot                  | boolean | ✓              |
| `language_code`    | User's language code                   | string  | ✗              |
| `command`          | Command name (without /)               | string  | Commands only  |
| `cattackle_name`   | Name of cattackle that handled command | string  | Commands only  |
| `response_length`  | Length of bot's response               | number  | Commands only  |

## Configuration

The chat logging system can be configured via environment variables or settings:

```python
# In .env file
CHAT_LOGS_DIR=logs/chats

# Or in settings
chat_logs_dir: str = "logs/chats"
```

## Analysis Commands

The system includes several Makefile commands for analyzing chat logs:

### Basic Analysis

```bash
# Show summary analysis of all chat logs
make analyze-chats

# Show summary analysis in JSON format
make analyze-chats-json

# Show unique participants analysis
make analyze-participants

# Show commands usage analysis
make analyze-commands
```

### Date-Filtered Analysis

```bash
# Analyze logs for a specific date
make analyze-chats-date DATE=2024-01-15
```

### Help

```bash
# Show all available analysis commands
make help-analyze
```

## Direct Script Usage

You can also use the analysis script directly for more advanced options:

```bash
# Show help for all options
uv run python scripts/analyze_chats.py --help

# Analyze specific date range
uv run python scripts/analyze_chats.py --date 2024-01-15

# Get daily activity breakdown
uv run python scripts/analyze_chats.py --output daily

# Export results as JSON
uv run python scripts/analyze_chats.py --output summary --format json
```

## Analysis Output Examples

### Summary Analysis

```
=== CHAT LOG ANALYSIS SUMMARY ===
Total log entries: 8
Unique chats: 3
Unique participants: 3
Total commands executed: 4
Unique commands: 3
Date range: 2024-01-15 to 2024-01-16

=== TOP PARTICIPANTS ===
@alice: 4 messages
Bob Smith: 2 messages
Charlie: 2 messages

=== TOP COMMANDS ===
/echo: 2 times
/ping: 1 times
/status: 1 times
```

### Daily Activity

```
=== DAILY ACTIVITY ===
2024-01-15: 5 messages (2 commands, 3 regular), 2 users, 2 chats
2024-01-16: 3 messages (2 commands, 1 regular), 2 users, 2 chats
```

## Privacy Considerations

- **Text Preview**: Only the first 100 characters of messages are stored for privacy
- **User Information**: Only public Telegram user data is logged (username, first name, etc.)
- **No Message Content**: Full message content is not stored in logs
- **Local Storage**: All logs are stored locally in the configured directory

## File Structure

```
logs/
└── chats/
    ├── 2024-01-15.jsonl
    ├── 2024-01-16.jsonl
    └── 2024-01-17.jsonl
```

## Integration

The chat logging system is automatically integrated into the message routing system and requires no additional setup beyond configuration. All chat interactions are logged automatically when the bot processes messages.

## Troubleshooting

### No Log Files Created

1. Check that the `chat_logs_dir` directory exists and is writable
2. Verify the bot is receiving and processing messages
3. Check application logs for any chat logger errors

### Analysis Commands Not Working

1. Ensure log files exist in the configured directory
2. Check that the analysis script has proper permissions
3. Verify the date format for date-filtered commands (YYYY-MM-DD)

### Empty Analysis Results

1. Confirm log files contain valid JSON entries
2. Check that the date filter matches existing log files
3. Verify log files are not empty or corrupted
