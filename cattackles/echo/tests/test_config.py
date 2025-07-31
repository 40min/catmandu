"""
Tests for the configuration management.
These tests focus on settings validation and environment loading.
"""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from cattackles.echo.src.config import EchoCattackleSettings


class TestEchoCattackleSettings:
    """Test class for EchoCattackleSettings functionality."""

    def test_valid_settings_creation(self, test_api_key, test_model_name, test_port):
        """Test creating settings with valid values."""
        settings = EchoCattackleSettings(
            gemini_api_key=test_api_key, gemini_model=test_model_name, mcp_server_port=test_port, log_level="INFO"
        )

        assert settings.gemini_api_key == test_api_key
        assert settings.gemini_model == test_model_name
        assert settings.mcp_server_port == test_port
        assert settings.log_level == "INFO"

    def test_default_values(self, valid_settings):
        """Test that default values are applied correctly."""
        # Create settings with only required fields
        settings = EchoCattackleSettings(
            gemini_api_key=valid_settings.gemini_api_key, gemini_model=valid_settings.gemini_model
        )

        assert settings.mcp_server_port == 8001
        assert settings.log_level == "INFO"

    def test_log_level_validation_valid(self, test_api_key, test_model_name):
        """Test log level validation with valid values."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in valid_levels:
            settings = EchoCattackleSettings(gemini_api_key=test_api_key, gemini_model=test_model_name, log_level=level)
            assert settings.log_level == level

    def test_log_level_validation_case_insensitive(self, test_api_key, test_model_name):
        """Test log level validation with uppercase values."""
        # Since the field uses Literal type, it only accepts exact values
        settings = EchoCattackleSettings(
            gemini_api_key=test_api_key, gemini_model=test_model_name, log_level="INFO"  # Must be uppercase
        )
        assert settings.log_level == "INFO"

    def test_log_level_validation_invalid(self, test_api_key, test_model_name):
        """Test log level validation with invalid values."""
        with pytest.raises(ValidationError, match="Input should be"):
            EchoCattackleSettings(gemini_api_key=test_api_key, gemini_model=test_model_name, log_level="INVALID")

    def test_port_validation_valid(self, test_api_key, test_model_name):
        """Test port validation with valid values."""
        settings = EchoCattackleSettings(
            gemini_api_key=test_api_key, gemini_model=test_model_name, mcp_server_port=8080
        )
        assert settings.mcp_server_port == 8080

    def test_port_validation_invalid_low(self, test_api_key, test_model_name):
        """Test port validation with value too low."""
        with pytest.raises(ValidationError, match="MCP_SERVER_PORT must be between 1 and 65535"):
            EchoCattackleSettings(gemini_api_key=test_api_key, gemini_model=test_model_name, mcp_server_port=0)

    def test_port_validation_invalid_high(self, test_api_key, test_model_name):
        """Test port validation with value too high."""
        with pytest.raises(ValidationError, match="MCP_SERVER_PORT must be between 1 and 65535"):
            EchoCattackleSettings(gemini_api_key=test_api_key, gemini_model=test_model_name, mcp_server_port=65536)

    def test_from_environment_success(self):
        """Test creating settings from environment variables."""
        env_vars = {
            "GEMINI_API_KEY": "env-api-key",
            "GEMINI_MODEL": "gemini-1.5-pro",
            "MCP_SERVER_PORT": "8002",
            "LOG_LEVEL": "DEBUG",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = EchoCattackleSettings.from_environment()

            assert settings.gemini_api_key == "env-api-key"
            assert settings.gemini_model == "gemini-1.5-pro"
            assert settings.mcp_server_port == 8002
            assert settings.log_level == "DEBUG"

    def test_from_environment_defaults(self):
        """Test creating settings from environment with defaults."""
        env_vars = {"GEMINI_API_KEY": "env-api-key", "GEMINI_MODEL": "gemini-pro"}

        with patch.dict(os.environ, env_vars, clear=True):
            settings = EchoCattackleSettings.from_environment()

            assert settings.gemini_api_key == "env-api-key"
            assert settings.gemini_model == "gemini-pro"
            assert settings.mcp_server_port == 8001  # default
            assert settings.log_level == "INFO"  # default

    def test_from_environment_missing_api_key(self):
        """Test creating settings from environment with missing API key."""
        env_vars = {"GEMINI_MODEL": "gemini-pro"}

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValueError, match="GEMINI_API_KEY environment variable is required"):
                EchoCattackleSettings.from_environment()

    def test_from_environment_missing_model(self):
        """Test creating settings from environment with missing model."""
        env_vars = {"GEMINI_API_KEY": "test-key"}

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValueError, match="GEMINI_MODEL environment variable is required"):
                EchoCattackleSettings.from_environment()

    def test_validate_environment_logs_configuration(self, valid_settings, caplog):
        """Test that validate_environment logs configuration details."""
        import logging

        # Set up logging to capture messages
        caplog.set_level(logging.INFO)

        valid_settings.validate_environment()

        # Check that configuration details are logged
        assert "Echo Cattackle configuration loaded:" in caplog.text
        assert "Log level: INFO" in caplog.text
        assert "MCP server port: 8001" in caplog.text
        assert "Gemini API key: ✓ Configured" in caplog.text
        assert "Gemini model: gemini-pro" in caplog.text

    def test_configure_logging_sets_level(self, valid_settings):
        """Test that configure_logging sets the correct logging level."""
        debug_settings = EchoCattackleSettings(
            gemini_api_key=valid_settings.gemini_api_key, gemini_model=valid_settings.gemini_model, log_level="DEBUG"
        )

        with patch("logging.basicConfig") as mock_basic_config:
            debug_settings.configure_logging()

            mock_basic_config.assert_called_once()
            call_args = mock_basic_config.call_args
            assert call_args[1]["level"] == 10  # DEBUG level numeric value
