import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from catmandu.core.services.chat_logger import ChatLogger


class TestChatLogger:
    """Test cases for ChatLogger service."""

    @pytest.fixture
    def temp_logs_dir(self):
        """Create a temporary directory for test logs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def chat_logger(self, temp_logs_dir):
        """Create a ChatLogger instance with temporary directory."""
        return ChatLogger(logs_dir=temp_logs_dir)

    def test_log_message_creates_daily_file(self, chat_logger, temp_logs_dir):
        """Test that logging a message creates a daily log file."""
        chat_logger.log_message(
            chat_id=123,
            message_type="message",
            text="Hello world",
            user_info={"username": "testuser", "first_name": "Test", "id": 456},
        )

        # Check that log file was created
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = Path(temp_logs_dir) / f"{today}.jsonl"
        assert log_file.exists()

        # Check log content
        with open(log_file, "r", encoding="utf-8") as f:
            line = f.readline().strip()
            entry = json.loads(line)

        assert entry["chat_id"] == 123
        assert entry["participant_name"] == "@testuser"
        assert entry["message_type"] == "message"
        assert entry["text_length"] == 11
        assert entry["text_preview"] == "Hello world"
        assert entry["user_id"] == 456

    def test_log_command_message(self, chat_logger, temp_logs_dir):
        """Test logging a command message."""
        chat_logger.log_message(
            chat_id=789,
            message_type="command",
            text="/echo hello",
            user_info={"first_name": "John", "last_name": "Doe", "id": 101},
            command="echo",
            cattackle_name="echo",
            response_length=50,
        )

        today = datetime.now().strftime("%Y-%m-%d")
        log_file = Path(temp_logs_dir) / f"{today}.jsonl"

        with open(log_file, "r", encoding="utf-8") as f:
            entry = json.loads(f.readline().strip())

        assert entry["chat_id"] == 789
        assert entry["participant_name"] == "John Doe"
        assert entry["message_type"] == "command"
        assert entry["command"] == "echo"
        assert entry["cattackle_name"] == "echo"
        assert entry["response_length"] == 50

    def test_log_multiple_messages_same_day(self, chat_logger, temp_logs_dir):
        """Test that multiple messages on the same day are appended to the same file."""
        chat_logger.log_message(
            chat_id=111, message_type="message", text="First message", user_info={"username": "user1"}
        )

        chat_logger.log_message(
            chat_id=222, message_type="command", text="/test", user_info={"username": "user2"}, command="test"
        )

        today = datetime.now().strftime("%Y-%m-%d")
        log_file = Path(temp_logs_dir) / f"{today}.jsonl"

        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        assert len(lines) == 2

        entry1 = json.loads(lines[0].strip())
        entry2 = json.loads(lines[1].strip())

        assert entry1["chat_id"] == 111
        assert entry1["participant_name"] == "@user1"
        assert entry2["chat_id"] == 222
        assert entry2["participant_name"] == "@user2"

    def test_participant_name_fallback(self, chat_logger, temp_logs_dir):
        """Test participant name extraction with various user info scenarios."""
        # Test with no user info
        chat_logger.log_message(chat_id=123, message_type="message", text="Test", user_info=None)

        # Test with empty user info
        chat_logger.log_message(chat_id=124, message_type="message", text="Test", user_info={})

        # Test with only first name
        chat_logger.log_message(chat_id=125, message_type="message", text="Test", user_info={"first_name": "Alice"})

        today = datetime.now().strftime("%Y-%m-%d")
        log_file = Path(temp_logs_dir) / f"{today}.jsonl"

        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        entries = [json.loads(line.strip()) for line in lines]

        assert entries[0]["participant_name"] == "Unknown"
        assert entries[1]["participant_name"] == "Unknown"
        assert entries[2]["participant_name"] == "Alice"

    def test_get_log_files(self, chat_logger, temp_logs_dir):
        """Test getting list of log files."""
        # Initially no files
        assert chat_logger.get_log_files() == []

        # Create some log entries
        chat_logger.log_message(123, "message", "test", {})

        log_files = chat_logger.get_log_files()
        assert len(log_files) == 1
        assert log_files[0].suffix == ".jsonl"

    def test_get_date_range(self, chat_logger, temp_logs_dir):
        """Test getting date range of logs."""
        # No logs initially
        start, end = chat_logger.get_date_range()
        assert start is None
        assert end is None

        # Add a log entry
        chat_logger.log_message(123, "message", "test", {})

        start, end = chat_logger.get_date_range()
        today = datetime.now().strftime("%Y-%m-%d")
        assert start == today
        assert end == today
