import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import structlog


class ChatLogger:
    """Infrastructure component for logging chat interactions to daily files."""

    def __init__(self, logs_dir: str = "logs/chats"):
        self.log = structlog.get_logger(self.__class__.__name__)
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def log_message(
        self,
        chat_id: int,
        message_type: str,  # "command" or "message"
        text: str,
        user_info: Optional[Dict] = None,
        command: Optional[str] = None,
        cattackle_name: Optional[str] = None,
        response_length: Optional[int] = None,
    ) -> None:
        """Log a chat interaction to daily file.

        Args:
            chat_id: Telegram chat ID
            message_type: Type of message ("command" or "message")
            text: Message text
            user_info: User information from Telegram message
            command: Command name if it's a command message
            cattackle_name: Cattackle name if it's a command
            response_length: Length of bot response if applicable
        """
        try:
            # Get current date for filename
            today = datetime.now().strftime("%Y-%m-%d")
            log_file = self.logs_dir / f"{today}.jsonl"

            # Extract user information
            participant_name = "Unknown"
            if user_info:
                if user_info.get("username"):
                    participant_name = f"@{user_info['username']}"
                elif user_info.get("first_name"):
                    participant_name = user_info["first_name"]
                    if user_info.get("last_name"):
                        participant_name += f" {user_info['last_name']}"

            # Create log entry
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "chat_id": chat_id,
                "participant_name": participant_name,
                "message_type": message_type,
                "text_length": len(text),
                "text_preview": text[:100] + "..." if len(text) > 100 else text,
            }

            # Add command-specific fields
            if command:
                log_entry["command"] = command
            if cattackle_name:
                log_entry["cattackle_name"] = cattackle_name
            if response_length is not None:
                log_entry["response_length"] = response_length

            # Add user details if available
            if user_info:
                log_entry["user_id"] = user_info.get("id")
                log_entry["is_bot"] = user_info.get("is_bot", False)
                if user_info.get("language_code"):
                    log_entry["language_code"] = user_info["language_code"]

            # Write to file (append mode)
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

            self.log.debug(
                "Chat interaction logged",
                chat_id=chat_id,
                message_type=message_type,
                participant_name=participant_name,
                log_file=str(log_file),
            )

        except Exception as e:
            self.log.error("Failed to log chat interaction", error=e, chat_id=chat_id)

    def get_log_files(self) -> list[Path]:
        """Get list of all log files."""
        return sorted(self.logs_dir.glob("*.jsonl"))

    def get_date_range(self) -> tuple[Optional[str], Optional[str]]:
        """Get the date range of available logs."""
        log_files = self.get_log_files()
        if not log_files:
            return None, None

        dates = [f.stem for f in log_files]
        return min(dates), max(dates)
