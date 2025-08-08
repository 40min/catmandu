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
    openai_model: str = Field(default="gpt-5-nano", description="OpenAI model for text improvement")
    audio_processing_enabled: bool = Field(default=False, description="Enable audio processing features")

    # Audio processing limits
    max_audio_file_size_mb: int = Field(default=25, description="Maximum audio file size in MB")
    max_audio_duration_minutes: int = Field(default=10, description="Maximum audio duration in minutes")

    # Cost tracking configuration
    whisper_cost_per_minute: float = Field(default=0.006, description="Whisper API cost per minute")
    openai_gpt_nano_input_cost_per_1m_tokens: float = Field(
        default=0.15, description="OpenAI model input cost per 1M tokens"
    )
    openai_gpt_nano_output_cost_per_1m_tokens: float = Field(
        default=0.60, description="OpenAI model output cost per 1M tokens"
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
                raise ValueError(
                    "OpenAI API key must start with 'sk-'. " "Please check your OPENAI_API_KEY environment variable."
                )
            # Basic length check - real OpenAI keys are much longer, but allow shorter ones for testing
            if len(v) < 10:
                raise ValueError(
                    "OpenAI API key appears to be invalid (too short). "
                    "Please verify your OPENAI_API_KEY environment variable."
                )
        return v

    @field_validator("max_audio_file_size_mb")
    @classmethod
    def validate_max_audio_file_size_mb(cls, v: int) -> int:
        """Validate maximum audio file size."""
        if v <= 0:
            raise ValueError("MAX_AUDIO_FILE_SIZE_MB must be greater than 0")
        if v > 50:  # Telegram's file size limit is 50MB
            raise ValueError("MAX_AUDIO_FILE_SIZE_MB cannot exceed 50MB (Telegram's limit)")
        return v

    @field_validator("max_audio_duration_minutes")
    @classmethod
    def validate_max_audio_duration_minutes(cls, v: int) -> int:
        """Validate maximum audio duration."""
        if v <= 0:
            raise ValueError("MAX_AUDIO_DURATION_MINUTES must be greater than 0")
        if v > 60:  # Reasonable upper limit
            raise ValueError("MAX_AUDIO_DURATION_MINUTES cannot exceed 60 minutes")
        return v

    @field_validator("whisper_cost_per_minute")
    @classmethod
    def validate_whisper_cost_per_minute(cls, v: float) -> float:
        """Validate Whisper API cost per minute."""
        if v < 0:
            raise ValueError("WHISPER_COST_PER_MINUTE must be non-negative")
        return v

    @field_validator("openai_gpt_nano_input_cost_per_1m_tokens")
    @classmethod
    def validate_openai_gpt_nano_input_cost_per_1m_tokens(cls, v: float) -> float:
        """Validate OpenAI model input cost per 1M tokens."""
        if v < 0:
            raise ValueError("OPENAI_GPT_NANO_INPUT_COST_PER_1M_TOKENS must be non-negative")
        return v

    @field_validator("openai_gpt_nano_output_cost_per_1m_tokens")
    @classmethod
    def validate_openai_gpt_nano_output_cost_per_1m_tokens(cls, v: float) -> float:
        """Validate OpenAI model output cost per 1M tokens."""
        if v < 0:
            raise ValueError("OPENAI_GPT_NANO_OUTPUT_COST_PER_1M_TOKENS must be non-negative")
        return v

    def validate_environment(self) -> None:
        """Validate critical environment variables and log configuration status."""
        logger = logging.getLogger(__name__)
        validation_errors = []

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
            logger.info(f"  - Whisper cost per minute: ${self.whisper_cost_per_minute:.4f}")
            logger.info(
                f"  - OpenAI model input cost per 1M tokens: ${self.openai_gpt_nano_input_cost_per_1m_tokens:.2f}"
            )
            logger.info(
                f"  - OpenAI model output cost per 1M tokens: ${self.openai_gpt_nano_output_cost_per_1m_tokens:.2f}"
            )
        else:
            logger.info("  - Audio processing is disabled. Voice messages will not be processed.")
            logger.info("  - To enable audio processing, set AUDIO_PROCESSING_ENABLED=true and provide OPENAI_API_KEY")

        # Validate required environment variables
        if not self.telegram_bot_token:
            validation_errors.append(
                "TELEGRAM_BOT_TOKEN is required but not provided. "
                "Please set it in your environment variables or .env file."
            )

        # Validate audio processing configuration
        if self.audio_processing_enabled:
            if not self.openai_api_key:
                validation_errors.append(
                    "OPENAI_API_KEY is required when audio processing is enabled. "
                    "Please provide a valid OpenAI API key or set AUDIO_PROCESSING_ENABLED=false."
                )

            # Additional validation for audio processing settings
            try:
                import os

                if self.cost_logs_dir and not os.path.exists(os.path.dirname(self.cost_logs_dir) or "."):
                    logger.warning(f"Cost logs directory parent does not exist: {self.cost_logs_dir}")
            except Exception as e:
                logger.warning(f"Could not validate cost logs directory: {e}")

        # Report validation errors and exit if any critical issues found
        if validation_errors:
            logger.error("Configuration validation failed:")
            for error in validation_errors:
                logger.error(f"  ✗ {error}")
            logger.error("Please fix the configuration issues above and restart the application.")
            sys.exit(1)

        logger.info("✓ Configuration validation completed successfully")

    def is_audio_processing_available(self) -> bool:
        """Check if audio processing is properly configured and available."""
        return self.audio_processing_enabled and self.openai_api_key is not None

    def get_audio_processing_status_message(self) -> str:
        """Get a user-friendly message about audio processing availability."""
        if not self.audio_processing_enabled:
            return "Audio processing is currently disabled. " "Voice messages and audio files cannot be processed."
        elif not self.openai_api_key:
            return "Audio processing is enabled but not properly configured. " "OpenAI API key is missing."
        else:
            return "Audio processing is enabled and properly configured."

    def validate_audio_processing_requirements(self) -> None:
        """Validate that audio processing requirements are met if enabled."""
        from catmandu.core.errors import AudioProcessingConfigurationError

        if self.audio_processing_enabled and not self.openai_api_key:
            raise AudioProcessingConfigurationError(
                "Audio processing is enabled but OPENAI_API_KEY is not provided. "
                "Please set OPENAI_API_KEY environment variable or disable audio processing "
                "by setting AUDIO_PROCESSING_ENABLED=false."
            )
