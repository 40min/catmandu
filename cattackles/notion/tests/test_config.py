"""Tests for configuration management."""

import logging
import os
import tempfile
from unittest.mock import patch

import pytest
import structlog
from notion.config.settings import NotionCattackleSettings, configure_logging, get_settings, validate_environment
from pydantic import ValidationError


class TestNotionCattackleSettings:
    """Test the NotionCattackleSettings class."""

    def test_default_settings(self):
        """Test that default settings are correct."""
        settings = NotionCattackleSettings()

        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
        assert settings.log_level == "INFO"
        assert settings.log_format == "json"

    def test_environment_variable_override(self):
        """Test that environment variables override defaults."""
        with patch.dict(
            os.environ, {"HOST": "127.0.0.1", "PORT": "9000", "LOG_LEVEL": "DEBUG", "LOG_FORMAT": "console"}
        ):
            settings = NotionCattackleSettings()

            assert settings.host == "127.0.0.1"
            assert settings.port == 9000
            assert settings.log_level == "DEBUG"
            assert settings.log_format == "console"

    def test_case_insensitive_environment_variables(self):
        """Test that environment variables are case insensitive."""
        with patch.dict(os.environ, {"log_level": "warning", "LOG_FORMAT": "CONSOLE"}):
            settings = NotionCattackleSettings()

            assert settings.log_level == "WARNING"
            assert settings.log_format == "console"

    def test_env_file_loading(self):
        """Test loading configuration from .env file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("HOST=192.168.1.1\n")
            f.write("PORT=7000\n")
            f.write("LOG_LEVEL=ERROR\n")
            f.flush()

            try:
                settings = NotionCattackleSettings(_env_file=f.name)

                assert settings.host == "192.168.1.1"
                assert settings.port == 7000
                assert settings.log_level == "ERROR"
            finally:
                os.unlink(f.name)

    def test_invalid_log_level_validation(self):
        """Test that invalid log levels are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            NotionCattackleSettings(log_level="INVALID")

        assert "log_level must be one of" in str(exc_info.value)

    def test_valid_log_levels(self):
        """Test that all valid log levels are accepted."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in valid_levels:
            settings = NotionCattackleSettings(log_level=level)
            assert settings.log_level == level

            # Test lowercase versions
            settings = NotionCattackleSettings(log_level=level.lower())
            assert settings.log_level == level

    def test_invalid_log_format_validation(self):
        """Test that invalid log formats are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            NotionCattackleSettings(log_format="invalid")

        assert "log_format must be one of" in str(exc_info.value)

    def test_valid_log_formats(self):
        """Test that valid log formats are accepted."""
        valid_formats = ["json", "console"]

        for format_type in valid_formats:
            settings = NotionCattackleSettings(log_format=format_type)
            assert settings.log_format == format_type

            # Test uppercase versions
            settings = NotionCattackleSettings(log_format=format_type.upper())
            assert settings.log_format == format_type

    def test_invalid_port_validation(self):
        """Test that invalid ports are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            NotionCattackleSettings(port=0)

        assert "port must be between 1 and 65535" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            NotionCattackleSettings(port=65536)

        assert "port must be between 1 and 65535" in str(exc_info.value)

    def test_valid_port_range(self):
        """Test that valid ports are accepted."""
        # Test boundary values
        settings = NotionCattackleSettings(port=1)
        assert settings.port == 1

        settings = NotionCattackleSettings(port=65535)
        assert settings.port == 65535

        # Test common values
        settings = NotionCattackleSettings(port=8080)
        assert settings.port == 8080


class TestConfigureLogging:
    """Test the configure_logging function."""

    def test_json_logging_configuration(self):
        """Test JSON logging configuration."""
        settings = NotionCattackleSettings(log_level="DEBUG", log_format="json")

        configure_logging(settings)

        # Verify that structlog is configured
        logger = structlog.get_logger("test")
        assert logger is not None

        # Verify logging level is set
        assert logging.getLogger().level == logging.DEBUG

    def test_console_logging_configuration(self):
        """Test console logging configuration."""
        settings = NotionCattackleSettings(log_level="WARNING", log_format="console")

        configure_logging(settings)

        # Verify that structlog is configured
        logger = structlog.get_logger("test")
        assert logger is not None

        # Verify logging level is set
        assert logging.getLogger().level == logging.WARNING

    def test_different_log_levels(self):
        """Test that different log levels are properly set."""
        levels = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }

        for level_name, level_value in levels.items():
            settings = NotionCattackleSettings(log_level=level_name)
            configure_logging(settings)

            assert logging.getLogger().level == level_value


class TestGetSettings:
    """Test the get_settings function."""

    def test_get_settings_returns_instance(self):
        """Test that get_settings returns a NotionCattackleSettings instance."""
        settings = get_settings()

        assert isinstance(settings, NotionCattackleSettings)
        assert settings.host == "0.0.0.0"  # Default value

    def test_get_settings_with_environment(self):
        """Test that get_settings respects environment variables."""
        with patch.dict(os.environ, {"PORT": "9999"}):
            settings = get_settings()

            assert settings.port == 9999


class TestValidateEnvironment:
    """Test the validate_environment function."""

    def test_valid_environment(self):
        """Test validation with valid environment."""
        with patch.dict(os.environ, {"HOST": "localhost", "PORT": "8080", "LOG_LEVEL": "INFO", "LOG_FORMAT": "json"}):
            result = validate_environment()

            assert result is True

    def test_invalid_environment_port(self):
        """Test validation with invalid port."""
        with patch.dict(os.environ, {"PORT": "99999"}):
            result = validate_environment()

            assert result is False

    def test_invalid_environment_log_level(self):
        """Test validation with invalid log level."""
        with patch.dict(os.environ, {"LOG_LEVEL": "INVALID"}):
            result = validate_environment()

            assert result is False

    def test_invalid_environment_log_format(self):
        """Test validation with invalid log format."""
        with patch.dict(os.environ, {"LOG_FORMAT": "invalid"}):
            result = validate_environment()

            assert result is False

    @patch("notion.config.settings.configure_logging")
    def test_logging_configuration_error(self, mock_configure):
        """Test validation when logging configuration fails."""
        mock_configure.side_effect = Exception("Logging configuration failed")

        result = validate_environment()

        assert result is False

    def test_validation_logs_success(self, caplog):
        """Test that successful validation is logged."""
        with caplog.at_level(logging.INFO):
            result = validate_environment()

            assert result is True
            # Note: We can't easily test structlog output in caplog,
            # but we can verify the function completes successfully
