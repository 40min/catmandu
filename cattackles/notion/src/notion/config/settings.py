"""Configuration management for the Notion cattackle."""

import logging

import structlog
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class NotionCattackleSettings(BaseSettings):
    """Settings for the Notion cattackle server."""

    # Server configuration
    host: str = Field(default="0.0.0.0", description="Server host address")
    port: int = Field(default=8000, description="Server port")

    # Logging configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format (json or console)")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate that log level is a valid logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v_upper

    @field_validator("log_format")
    @classmethod
    def validate_log_format(cls, v: str) -> str:
        """Validate that log format is supported."""
        valid_formats = ["json", "console"]
        v_lower = v.lower()
        if v_lower not in valid_formats:
            raise ValueError(f"log_format must be one of {valid_formats}")
        return v_lower

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate that port is in valid range."""
        if not (1 <= v <= 65535):
            raise ValueError("port must be between 1 and 65535")
        return v


def configure_logging(settings: NotionCattackleSettings) -> None:
    """Configure structured logging based on settings."""
    # Set the logging level
    log_level = getattr(logging, settings.log_level)

    # Configure structlog
    if settings.log_format == "json":
        # JSON format for production
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    else:
        # Console format for development
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.dev.ConsoleRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        level=log_level,
        force=True,  # Force reconfiguration
    )


def get_settings() -> NotionCattackleSettings:
    """Get the application settings."""
    return NotionCattackleSettings()


def validate_environment() -> bool:
    """Validate that the environment is properly configured."""
    try:
        settings = get_settings()

        # Validate that we can configure logging
        configure_logging(settings)

        # Log successful validation
        logger = structlog.get_logger(__name__)
        logger.info(
            "Environment validation successful",
            host=settings.host,
            port=settings.port,
            log_level=settings.log_level,
            log_format=settings.log_format,
        )

        return True

    except Exception as e:
        # Use basic logging since structured logging might not be configured
        logging.error(f"Environment validation failed: {e}")
        return False
