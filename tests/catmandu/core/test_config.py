import os
from unittest.mock import patch

from catmandu.core.config import Settings


class TestSettings:
    """Test suite for Settings configuration."""

    def test_default_accumulator_settings(self):
        """Test that accumulator settings have correct default values."""
        settings = Settings()

        assert settings.max_messages_per_chat == 100
        assert settings.max_message_length == 1000

    def test_custom_accumulator_settings_from_env(self):
        """Test that accumulator settings can be overridden via environment variables."""
        with patch.dict(
            os.environ,
            {"TELEGRAM_BOT_TOKEN": "dummy_token", "MAX_MESSAGES_PER_CHAT": "50", "MAX_MESSAGE_LENGTH": "500"},
        ):
            settings = Settings()

            assert settings.max_messages_per_chat == 50
            assert settings.max_message_length == 500

    def test_accumulator_settings_with_zero_values(self):
        """Test that accumulator settings can be set to zero."""
        with patch.dict(
            os.environ, {"TELEGRAM_BOT_TOKEN": "dummy_token", "MAX_MESSAGES_PER_CHAT": "0", "MAX_MESSAGE_LENGTH": "0"}
        ):
            settings = Settings()

            assert settings.max_messages_per_chat == 0
            assert settings.max_message_length == 0

    def test_accumulator_settings_with_large_values(self):
        """Test that accumulator settings can handle large values."""
        with patch.dict(
            os.environ,
            {"TELEGRAM_BOT_TOKEN": "dummy_token", "MAX_MESSAGES_PER_CHAT": "10000", "MAX_MESSAGE_LENGTH": "100000"},
        ):
            settings = Settings()

            assert settings.max_messages_per_chat == 10000
            assert settings.max_message_length == 100000

    def test_all_settings_together(self):
        """Test that all settings work together including the new accumulator settings."""
        with patch.dict(
            os.environ,
            {
                "TELEGRAM_BOT_TOKEN": "test_token_123",
                "CATTACKLES_DIR": "custom_cattackles",
                "UPDATE_ID_FILE_PATH": "custom/path/update_id.txt",
                "MAX_MESSAGES_PER_CHAT": "75",
                "MAX_MESSAGE_LENGTH": "750",
            },
        ):
            settings = Settings()

            assert settings.telegram_bot_token == "test_token_123"
            assert settings.cattackles_dir == "custom_cattackles"
            assert settings.update_id_file_path == "custom/path/update_id.txt"
            assert settings.max_messages_per_chat == 75
            assert settings.max_message_length == 750
