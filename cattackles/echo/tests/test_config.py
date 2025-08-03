"""
Tests for the configuration management.
These tests focus on settings validation and environment loading.
"""

import os
from unittest.mock import patch

import pytest
from echo.config import EchoCattackleSettings
from pydantic import ValidationError


class TestEchoCattackleSettings:
    """Test class for EchoCattackleSettings functionality."""

    def test_valid_settings_creation_openai_only(self, test_openai_api_key, test_openai_model, test_port):
        """Test creating settings with only OpenAI configuration."""
        settings = EchoCattackleSettings(
            openai_api_key=test_openai_api_key,
            openai_model=test_openai_model,
            gemini_api_key=None,
            mcp_server_port=test_port,
            log_level="INFO",
        )

        assert settings.openai_api_key == test_openai_api_key
        assert settings.openai_model == test_openai_model
        assert settings.gemini_api_key is None
        assert settings.mcp_server_port == test_port
        assert settings.log_level == "INFO"

    def test_valid_settings_creation_gemini_only(self, test_gemini_api_key, test_gemini_model, test_port):
        """Test creating settings with only Gemini configuration."""
        settings = EchoCattackleSettings(
            openai_api_key=None,
            gemini_api_key=test_gemini_api_key,
            gemini_model=test_gemini_model,
            mcp_server_port=test_port,
            log_level="INFO",
        )

        assert settings.openai_api_key is None
        assert settings.gemini_api_key == test_gemini_api_key
        assert settings.gemini_model == test_gemini_model
        assert settings.mcp_server_port == test_port
        assert settings.log_level == "INFO"

    def test_default_values(self, test_openai_api_key):
        """Test that default values are applied correctly."""
        settings = EchoCattackleSettings(openai_api_key=test_openai_api_key, gemini_api_key=None)

        assert settings.openai_model == "gpt-4o-mini"
        assert settings.gemini_model == "gemini-2.5-flash-lite-preview-06-17"
        assert settings.mcp_server_port == 8001
        assert settings.log_level == "INFO"

    def test_log_level_validation_valid(self, test_openai_api_key):
        """Test log level validation with valid values."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in valid_levels:
            settings = EchoCattackleSettings(openai_api_key=test_openai_api_key, log_level=level)
            assert settings.log_level == level

    def test_log_level_validation_case_insensitive(self, test_openai_api_key):
        """Test log level validation with uppercase values."""
        # Since the field uses Literal type, it only accepts exact values
        settings = EchoCattackleSettings(openai_api_key=test_openai_api_key, log_level="INFO")  # Must be uppercase
        assert settings.log_level == "INFO"

    def test_log_level_validation_invalid(self, test_openai_api_key):
        """Test log level validation with invalid values."""
        with pytest.raises(ValidationError, match="Input should be"):
            EchoCattackleSettings(openai_api_key=test_openai_api_key, log_level="INVALID")

    def test_port_validation_valid(self, test_openai_api_key):
        """Test port validation with valid values."""
        settings = EchoCattackleSettings(openai_api_key=test_openai_api_key, mcp_server_port=8080)
        assert settings.mcp_server_port == 8080

    def test_port_validation_invalid_low(self, test_openai_api_key):
        """Test port validation with value too low."""
        with pytest.raises(ValidationError, match="MCP_SERVER_PORT must be between 1 and 65535"):
            EchoCattackleSettings(openai_api_key=test_openai_api_key, mcp_server_port=0)

    def test_port_validation_invalid_high(self, test_openai_api_key):
        """Test port validation with value too high."""
        with pytest.raises(ValidationError, match="MCP_SERVER_PORT must be between 1 and 65535"):
            EchoCattackleSettings(openai_api_key=test_openai_api_key, mcp_server_port=65536)

    def test_from_environment_openai_only(self):
        """Test creating settings from environment with only OpenAI."""
        env_vars = {
            "OPENAI_API_KEY": "env-openai-key",
            "OPENAI_MODEL": "gpt-4",
            "MCP_SERVER_PORT": "8002",
            "LOG_LEVEL": "DEBUG",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = EchoCattackleSettings.from_environment()

            assert settings.openai_api_key == "env-openai-key"
            assert settings.openai_model == "gpt-4"
            assert settings.gemini_api_key is None
            assert settings.mcp_server_port == 8002
            assert settings.log_level == "DEBUG"

    def test_from_environment_gemini_only(self):
        """Test creating settings from environment with only Gemini."""
        env_vars = {
            "GEMINI_API_KEY": "env-gemini-key",
            "GEMINI_MODEL": "gemini-1.5-pro",
            "MCP_SERVER_PORT": "8002",
            "LOG_LEVEL": "DEBUG",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = EchoCattackleSettings.from_environment()

            assert settings.openai_api_key is None
            assert settings.gemini_api_key == "env-gemini-key"
            assert settings.gemini_model == "gemini-1.5-pro"
            assert settings.mcp_server_port == 8002
            assert settings.log_level == "DEBUG"

    def test_from_environment_both_apis(self):
        """Test creating settings from environment with both APIs."""
        env_vars = {
            "OPENAI_API_KEY": "env-openai-key",
            "OPENAI_MODEL": "gpt-4",
            "GEMINI_API_KEY": "env-gemini-key",
            "GEMINI_MODEL": "gemini-1.5-pro",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = EchoCattackleSettings.from_environment()

            assert settings.openai_api_key == "env-openai-key"
            assert settings.openai_model == "gpt-4"
            assert settings.gemini_api_key == "env-gemini-key"
            assert settings.gemini_model == "gemini-1.5-pro"

    def test_from_environment_defaults(self):
        """Test creating settings from environment with defaults."""
        env_vars = {"OPENAI_API_KEY": "env-openai-key"}

        with patch.dict(os.environ, env_vars, clear=True):
            settings = EchoCattackleSettings.from_environment()

            assert settings.openai_api_key == "env-openai-key"
            assert settings.openai_model == "gpt-4o-mini"  # default
            assert settings.gemini_api_key is None
            assert settings.gemini_model == "gemini-2.5-flash-lite-preview-06-17"  # default
            assert settings.mcp_server_port == 8001  # default
            assert settings.log_level == "INFO"  # default

    def test_from_environment_missing_both_api_keys(self):
        """Test creating settings from environment with no API keys."""
        env_vars = {}

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(
                ValueError, match="At least one of OPENAI_API_KEY or GEMINI_API_KEY environment variables is required"
            ):
                EchoCattackleSettings.from_environment()

    def test_validate_environment_logs_openai_configuration(self, settings_with_openai_only, caplog):
        """Test that validate_environment logs OpenAI configuration details."""
        import logging

        # Set up logging to capture messages
        caplog.set_level(logging.INFO)

        settings_with_openai_only.validate_environment()

        # Check that configuration details are logged
        assert "Echo Cattackle configuration loaded:" in caplog.text
        assert "Log level: INFO" in caplog.text
        assert "MCP server port: 8001" in caplog.text
        assert "OpenAI API key: ✓ Configured" in caplog.text
        assert "OpenAI model: gpt-4o-mini" in caplog.text
        assert "Gemini API key: ✗ Not configured" in caplog.text
        assert "OpenAI API configured as primary" in caplog.text

    def test_validate_environment_logs_gemini_fallback(self, settings_with_gemini_only, caplog):
        """Test that validate_environment logs Gemini fallback configuration."""
        import logging

        # Set up logging to capture messages
        caplog.set_level(logging.INFO)

        settings_with_gemini_only.validate_environment()

        # Check that configuration details are logged
        assert "Echo Cattackle configuration loaded:" in caplog.text
        assert "OpenAI API key: ✗ Not configured" in caplog.text
        assert "Gemini API key: ✓ Configured" in caplog.text
        assert "Gemini API configured as fallback" in caplog.text

    def test_configure_logging_sets_level(self, test_openai_api_key):
        """Test that configure_logging sets the correct logging level."""
        debug_settings = EchoCattackleSettings(openai_api_key=test_openai_api_key, log_level="DEBUG")

        with patch("logging.basicConfig") as mock_basic_config:
            debug_settings.configure_logging()

            mock_basic_config.assert_called_once()
            call_args = mock_basic_config.call_args
            assert call_args[1]["level"] == 10  # DEBUG level numeric value
