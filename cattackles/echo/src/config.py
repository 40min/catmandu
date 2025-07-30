import logging
import os
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class EchoCattackleSettings(BaseModel):
    """Configuration settings for the Echo Cattackle."""

    # Gemini API configuration (required)
    gemini_api_key: str = Field(..., description="Required Gemini API key for joke functionality")
    gemini_model: str = Field(..., description="Required Gemini model to use for joke generation")

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
        # Get required environment variables, fail fast if missing
        gemini_api_key = os.environ.get("GEMINI_API_KEY")
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")

        gemini_model = os.environ.get("GEMINI_MODEL")
        if not gemini_model:
            raise ValueError("GEMINI_MODEL environment variable is required")

        return cls(
            gemini_api_key=gemini_api_key,
            gemini_model=gemini_model,
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
        logger.info("  - Gemini API key: ✓ Configured")
        logger.info(f"  - Gemini model: {self.gemini_model}")

        logger.info("Gemini API configured successfully. Joke functionality enabled.")

    def configure_logging(self) -> None:
        """Configure logging based on the log level setting."""
        numeric_level = getattr(logging, self.log_level.upper(), logging.INFO)

        logging.basicConfig(
            level=numeric_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            force=True,  # Override any existing configuration
        )
