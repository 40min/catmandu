import logging
import sys
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    cattackles_dir: str = Field(default="cattackles", description="Directory containing cattackle modules")
    telegram_bot_token: str = Field(..., description="Required Telegram bot token")
    update_id_file_path: str = Field(default=".data/update_id.txt", description="Path to store Telegram update offset")

    # Chat logging configuration
    chat_logs_dir: str = Field(default="logs/chats", description="Directory for chat logs")

    # Message accumulator configuration
    max_messages_per_chat: int = Field(default=100, description="Maximum messages per chat in accumulator")
    max_message_length: int = Field(default=1000, description="Maximum length of individual messages")

    # Logging configuration
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Logging level"
    )

    @field_validator("telegram_bot_token")
    @classmethod
    def validate_telegram_bot_token(cls, v: str) -> str:
        """Validate that the Telegram bot token is provided and not empty."""
        if not v or v.strip() == "":
            raise ValueError(
                "TELEGRAM_BOT_TOKEN is required. Please set it in your environment variables or .env file."
            )
        return v.strip()

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate and normalize log level."""
        v = v.upper()
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of: {', '.join(valid_levels)}")
        return v

    def validate_environment(self) -> None:
        """Validate critical environment variables and log configuration status."""
        logger = logging.getLogger(__name__)

        # Log configuration status
        logger.info("Configuration loaded successfully:")
        logger.info(f"  - Log level: {self.log_level}")
        logger.info(f"  - Telegram bot token: {'✓ Configured' if self.telegram_bot_token else '✗ Missing'}")
        logger.info(f"  - Update ID file path: {self.update_id_file_path}")
        logger.info(f"  - Max messages per chat: {self.max_messages_per_chat}")
        logger.info(f"  - Max message length: {self.max_message_length}")
        logger.info(f"  - Cattackles directory: {self.cattackles_dir}")
        logger.info(f"  - Chat logs directory: {self.chat_logs_dir}")

        # Validate required environment variables
        if not self.telegram_bot_token:
            logger.error("TELEGRAM_BOT_TOKEN is required but not provided")
            sys.exit(1)
