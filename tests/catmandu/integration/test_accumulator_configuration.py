import os
from unittest.mock import patch

from catmandu.core.config import Settings
from catmandu.core.services.accumulator import MessageAccumulator
from catmandu.core.services.accumulator_manager import AccumulatorManager


class TestAccumulatorConfiguration:
    """Test suite for verifying accumulator configuration is properly applied."""

    def test_accumulator_uses_default_config_values(self):
        """Test that MessageAccumulator uses default configuration values."""
        settings = Settings(telegram_bot_token="dummy_token")

        accumulator = MessageAccumulator(
            max_messages_per_chat=settings.max_messages_per_chat, max_message_length=settings.max_message_length
        )

        assert accumulator._max_messages == 100
        assert accumulator._max_message_length == 1000

    def test_accumulator_uses_custom_config_values(self):
        """Test that MessageAccumulator uses custom configuration values from environment."""
        with patch.dict(
            os.environ,
            {"TELEGRAM_BOT_TOKEN": "dummy_token", "MAX_MESSAGES_PER_CHAT": "50", "MAX_MESSAGE_LENGTH": "500"},
        ):
            settings = Settings()

            accumulator = MessageAccumulator(
                max_messages_per_chat=settings.max_messages_per_chat, max_message_length=settings.max_message_length
            )

            assert accumulator._max_messages == 50
            assert accumulator._max_message_length == 500

    def test_accumulator_configuration_affects_behavior(self):
        """Test that configuration values actually affect accumulator behavior."""
        with patch.dict(
            os.environ, {"TELEGRAM_BOT_TOKEN": "dummy_token", "MAX_MESSAGES_PER_CHAT": "2", "MAX_MESSAGE_LENGTH": "5"}
        ):
            settings = Settings()

            accumulator = MessageAccumulator(
                max_messages_per_chat=settings.max_messages_per_chat, max_message_length=settings.max_message_length
            )

            chat_id = 123

            # Test message length limit
            accumulator.add_message(chat_id, "This is a long message")
            messages = accumulator.get_messages(chat_id)
            assert len(messages) == 1
            assert messages[0] == "This "  # Truncated to 5 characters

            # Clear and test message count limit
            accumulator.clear_chat(chat_id)

            # Add more messages than the limit
            accumulator.add_message(chat_id, "Msg1")
            accumulator.add_message(chat_id, "Msg2")
            accumulator.add_message(chat_id, "Msg3")  # Should push out Msg1

            messages = accumulator.get_messages(chat_id)
            assert len(messages) == 2  # Limited to 2 messages
            assert messages == ["Msg2", "Msg3"]  # Most recent messages

    def test_accumulator_manager_with_configured_accumulator(self):
        """Test that AccumulatorManager works with configured accumulator."""
        with patch.dict(
            os.environ, {"TELEGRAM_BOT_TOKEN": "dummy_token", "MAX_MESSAGES_PER_CHAT": "3", "MAX_MESSAGE_LENGTH": "10"}
        ):
            settings = Settings()

            accumulator = MessageAccumulator(
                max_messages_per_chat=settings.max_messages_per_chat, max_message_length=settings.max_message_length
            )
            manager = AccumulatorManager(accumulator=accumulator, feedback_enabled=True)

            chat_id = 123

            # Test that manager respects accumulator configuration
            manager.process_non_command_message(chat_id, "This is a very long message that should be truncated")

            status = manager.get_accumulator_status(chat_id)
            assert "1 message" in status

            # Verify the message was truncated
            params = manager.get_all_parameters_and_clear(chat_id)
            assert len(params) == 1
            assert len(params[0]) == 10  # Truncated to max_message_length

    def test_zero_configuration_values(self):
        """Test behavior with zero configuration values."""
        with patch.dict(
            os.environ, {"TELEGRAM_BOT_TOKEN": "dummy_token", "MAX_MESSAGES_PER_CHAT": "0", "MAX_MESSAGE_LENGTH": "0"}
        ):
            settings = Settings()

            accumulator = MessageAccumulator(
                max_messages_per_chat=settings.max_messages_per_chat, max_message_length=settings.max_message_length
            )

            chat_id = 123

            # With zero message length, messages should be skipped
            accumulator.add_message(chat_id, "Any message")
            messages = accumulator.get_messages(chat_id)
            assert len(messages) == 0

    def test_large_configuration_values(self):
        """Test behavior with large configuration values."""
        with patch.dict(
            os.environ,
            {"TELEGRAM_BOT_TOKEN": "dummy_token", "MAX_MESSAGES_PER_CHAT": "1000", "MAX_MESSAGE_LENGTH": "10000"},
        ):
            settings = Settings()

            accumulator = MessageAccumulator(
                max_messages_per_chat=settings.max_messages_per_chat, max_message_length=settings.max_message_length
            )

            chat_id = 123

            # Should handle large values without issues
            long_message = "x" * 5000  # 5000 character message
            accumulator.add_message(chat_id, long_message)

            messages = accumulator.get_messages(chat_id)
            assert len(messages) == 1
            assert len(messages[0]) == 5000  # Should not be truncated

            # Should be able to store many messages
            for i in range(100):
                accumulator.add_message(chat_id, f"Message {i}")

            messages = accumulator.get_messages(chat_id)
            assert len(messages) == 101  # 1 original + 100 new messages
