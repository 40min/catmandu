import logging
import os
import sys
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class EchoCattackleSettings(BaseModel):
    """Configuration settings for the Echo Cattackle."""

    # OpenAI API configuration (primary for joke functionality)
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key for joke functionality")
    openai_model: str = Field(default="gpt-5-nano", description="OpenAI model to use for joke generation")

    # Gemini API configuration (fallback for joke functionality)
    gemini_api_key: Optional[str] = Field(default=None, description="Gemini API key for joke functionality")
    gemini_model: str = Field(
        default="gemini-2.5-flash-lite-preview-06-17", description="Gemini model to use for joke generation"
    )

    # Server configuration
    mcp_server_port: int = Field(default=8001, description="Port for the MCP HTTP server")

    # Logging configuration
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Logging level"
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate and normalize log level."""
        v = v.upper()
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of: {', '.join(valid_levels)}")
        return v

    @field_validator("mcp_server_port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate that the port is in valid range."""
        if not (1 <= v <= 65535):
            raise ValueError("MCP_SERVER_PORT must be between 1 and 65535")
        return v

    @classmethod
    def from_environment(cls) -> "EchoCattackleSettings":
        """Create settings from environment variables."""
        # Get API keys (at least one is required for joke functionality)
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        gemini_api_key = os.environ.get("GEMINI_API_KEY")

        if not openai_api_key and not gemini_api_key:
            raise ValueError(
                "At least one of OPENAI_API_KEY or GEMINI_API_KEY environment variables is required "
                "for joke functionality"
            )

        return cls(
            openai_api_key=openai_api_key,
            openai_model=os.environ.get("OPENAI_MODEL", "gpt-5-nano"),
            gemini_api_key=gemini_api_key,
            gemini_model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite-preview-06-17"),
            mcp_server_port=int(os.environ.get("MCP_SERVER_PORT", "8001")),
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
        )

    def validate_environment(self) -> None:
        """Validate environment configuration and log status."""
        logger = logging.getLogger(__name__)

        # Log configuration status
        logger.info("Echo Cattackle configuration loaded:")
        logger.info(f"  - Log level: {self.log_level}")
        logger.info(f"  - MCP server port: {self.mcp_server_port}")

        # Log API configuration status
        if self.openai_api_key:
            logger.info("  - OpenAI API key: ✓ Configured")
            logger.info(f"  - OpenAI model: {self.openai_model}")
        else:
            logger.info("  - OpenAI API key: ✗ Not configured")

        if self.gemini_api_key:
            logger.info("  - Gemini API key: ✓ Configured")
            logger.info(f"  - Gemini model: {self.gemini_model}")
        else:
            logger.info("  - Gemini API key: ✗ Not configured")

        # Determine primary model
        if self.openai_api_key:
            logger.info("OpenAI API configured as primary. Joke functionality enabled with configured OpenAI model.")
        elif self.gemini_api_key:
            logger.info("Gemini API configured as fallback. Joke functionality enabled with Gemini.")
        else:
            logger.warning("No AI API configured. Joke functionality will be disabled.")

    def configure_logging(self) -> None:
        """Configure logging based on the log level setting."""

        numeric_level = getattr(logging, self.log_level.upper(), logging.INFO)

        logging.basicConfig(
            level=numeric_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            stream=sys.stdout,  # Ensure logs go to stdout for Docker logging drivers
            force=True,  # Override any existing configuration
        )
