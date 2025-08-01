import os
from unittest.mock import patch

import pytest

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

    def test_openai_default_settings(self):
        """Test that OpenAI settings have correct default values."""
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "dummy_token"}):
            settings = Settings()

            assert settings.openai_api_key is None
            assert settings.audio_processing_enabled is False
            assert settings.max_audio_file_size_mb == 25
            assert settings.max_audio_duration_minutes == 10
            assert settings.whisper_cost_per_minute == 0.006
            assert settings.gpt4o_mini_input_cost_per_1m_tokens == 0.15
            assert settings.gpt4o_mini_output_cost_per_1m_tokens == 0.60
            assert settings.cost_logs_dir == "logs/costs"

    def test_openai_custom_settings_from_env(self):
        """Test that OpenAI settings can be overridden via environment variables."""
        with patch.dict(
            os.environ,
            {
                "TELEGRAM_BOT_TOKEN": "dummy_token",
                "OPENAI_API_KEY": "sk-test-key-123",
                "AUDIO_PROCESSING_ENABLED": "true",
                "MAX_AUDIO_FILE_SIZE_MB": "50",
                "MAX_AUDIO_DURATION_MINUTES": "15",
                "WHISPER_COST_PER_MINUTE": "0.008",
                "GPT4O_MINI_INPUT_COST_PER_1M_TOKENS": "0.20",
                "GPT4O_MINI_OUTPUT_COST_PER_1M_TOKENS": "0.80",
                "COST_LOGS_DIR": "custom/costs",
            },
        ):
            settings = Settings()

            assert settings.openai_api_key == "sk-test-key-123"
            assert settings.audio_processing_enabled is True
            assert settings.max_audio_file_size_mb == 50
            assert settings.max_audio_duration_minutes == 15
            assert settings.whisper_cost_per_minute == 0.008
            assert settings.gpt4o_mini_input_cost_per_1m_tokens == 0.20
            assert settings.gpt4o_mini_output_cost_per_1m_tokens == 0.80
            assert settings.cost_logs_dir == "custom/costs"

    def test_openai_api_key_validation_valid(self):
        """Test that valid OpenAI API keys are accepted."""
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "dummy_token", "OPENAI_API_KEY": "sk-valid-key-123"}):
            settings = Settings()
            assert settings.openai_api_key == "sk-valid-key-123"

    def test_openai_api_key_validation_invalid(self):
        """Test that invalid OpenAI API keys are rejected."""
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "dummy_token", "OPENAI_API_KEY": "invalid-key"}):
            with pytest.raises(ValueError, match="OpenAI API key must start with 'sk-'"):
                Settings()

    def test_openai_api_key_validation_empty_string(self):
        """Test that empty string API key is converted to None."""
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "dummy_token", "OPENAI_API_KEY": ""}):
            settings = Settings()
            assert settings.openai_api_key is None

    def test_openai_api_key_validation_whitespace(self):
        """Test that whitespace-only API key is converted to None."""
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "dummy_token", "OPENAI_API_KEY": "   "}):
            settings = Settings()
            assert settings.openai_api_key is None

    def test_validate_environment_audio_processing_enabled_without_api_key(self):
        """Test that validation fails when audio processing is enabled but API key is missing."""
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "dummy_token", "AUDIO_PROCESSING_ENABLED": "true"}):
            settings = Settings()

            with pytest.raises(SystemExit):
                settings.validate_environment()

    def test_validate_environment_audio_processing_enabled_with_api_key(self):
        """Test that validation passes when audio processing is enabled and API key is provided."""
        with patch.dict(
            os.environ,
            {
                "TELEGRAM_BOT_TOKEN": "dummy_token",
                "AUDIO_PROCESSING_ENABLED": "true",
                "OPENAI_API_KEY": "sk-valid-key-123",
            },
        ):
            settings = Settings()
            # Should not raise any exception
            settings.validate_environment()

    def test_validate_environment_audio_processing_disabled(self):
        """Test that validation passes when audio processing is disabled regardless of API key."""
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "dummy_token", "AUDIO_PROCESSING_ENABLED": "false"}):
            settings = Settings()
            # Should not raise any exception
            settings.validate_environment()
