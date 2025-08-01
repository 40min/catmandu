import logging
import sys
from typing import Literal, Optional

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

    # OpenAI configuration
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key for audio processing")
    audio_processing_enabled: bool = Field(default=False, description="Enable audio processing features")

    # Audio processing limits
    max_audio_file_size_mb: int = Field(default=25, description="Maximum audio file size in MB")
    max_audio_duration_minutes: int = Field(default=10, description="Maximum audio duration in minutes")

    # Cost tracking configuration
    whisper_cost_per_minute: float = Field(default=0.006, description="Whisper API cost per minute")
    gpt4o_mini_input_cost_per_1m_tokens: float = Field(default=0.15, description="GPT-4o-mini input cost per 1M tokens")
    gpt4o_mini_output_cost_per_1m_tokens: float = Field(
        default=0.60, description="GPT-4o-mini output cost per 1M tokens"
    )

    # Cost logging
    cost_logs_dir: str = Field(default="logs/costs", description="Directory for cost tracking logs")

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

    @field_validator("openai_api_key")
    @classmethod
    def validate_openai_api_key(cls, v: Optional[str]) -> Optional[str]:
        """Validate OpenAI API key format if provided."""
        if v is not None:
            v = v.strip()
            if v == "":
                return None
            if not v.startswith("sk-"):
                raise ValueError("OpenAI API key must start with 'sk-'")
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

        # Log audio processing configuration
        logger.info(f"  - Audio processing enabled: {self.audio_processing_enabled}")
        if self.audio_processing_enabled:
            logger.info(f"  - OpenAI API key: {'✓ Configured' if self.openai_api_key else '✗ Missing'}")
            logger.info(f"  - Max audio file size: {self.max_audio_file_size_mb}MB")
            logger.info(f"  - Max audio duration: {self.max_audio_duration_minutes} minutes")
            logger.info(f"  - Cost logs directory: {self.cost_logs_dir}")

        # Validate required environment variables
        if not self.telegram_bot_token:
            logger.error("TELEGRAM_BOT_TOKEN is required but not provided")
            sys.exit(1)

        # Validate audio processing configuration
        if self.audio_processing_enabled and not self.openai_api_key:
            logger.error("OPENAI_API_KEY is required when audio processing is enabled")
            sys.exit(1)
