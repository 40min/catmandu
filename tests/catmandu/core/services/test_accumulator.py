import pytest

from catmandu.core.services.accumulator import MessageAccumulator


@pytest.fixture
def accumulator():
    """Create a MessageAccumulator with default settings."""
    return MessageAccumulator()


@pytest.fixture
def accumulator_with_limits():
    """Create a MessageAccumulator with custom limits."""
    return MessageAccumulator(max_messages_per_chat=3, max_message_length=10)


class TestMessageAccumulator:
    """Test suite for MessageAccumulator service."""

    def test_init_default_settings(self):
        """Test initialization with default settings."""
        accumulator = MessageAccumulator()
        assert accumulator._max_messages == 100
        assert accumulator._max_message_length == 1000
        assert accumulator._messages == {}

    def test_init_custom_settings(self):
        """Test initialization with custom settings."""
        accumulator = MessageAccumulator(max_messages_per_chat=50, max_message_length=500)
        assert accumulator._max_messages == 50
        assert accumulator._max_message_length == 500
        assert accumulator._messages == {}

    def test_add_message_basic(self, accumulator):
        """Test adding a basic message."""
        chat_id = 123
        message = "Hello world"

        accumulator.add_message(chat_id, message)

        messages = accumulator.get_messages(chat_id)
        assert len(messages) == 1
        assert messages[0] == message

    def test_add_message_multiple_same_chat(self, accumulator):
        """Test adding multiple messages to the same chat."""
        chat_id = 123
        messages = ["First message", "Second message", "Third message"]

        for msg in messages:
            accumulator.add_message(chat_id, msg)

        stored_messages = accumulator.get_messages(chat_id)
        assert len(stored_messages) == 3
        assert stored_messages == messages

    def test_add_message_multiple_different_chats(self, accumulator):
        """Test adding messages to different chats."""
        chat1_id = 123
        chat2_id = 456

        accumulator.add_message(chat1_id, "Message for chat 1")
        accumulator.add_message(chat2_id, "Message for chat 2")
        accumulator.add_message(chat1_id, "Another message for chat 1")

        chat1_messages = accumulator.get_messages(chat1_id)
        chat2_messages = accumulator.get_messages(chat2_id)

        assert len(chat1_messages) == 2
        assert len(chat2_messages) == 1
        assert chat1_messages == ["Message for chat 1", "Another message for chat 1"]
        assert chat2_messages == ["Message for chat 2"]

    def test_add_message_empty_string(self, accumulator):
        """Test adding empty string message (should be skipped)."""
        chat_id = 123

        accumulator.add_message(chat_id, "")
        accumulator.add_message(chat_id, "   ")  # whitespace only
        accumulator.add_message(chat_id, "Valid message")

        messages = accumulator.get_messages(chat_id)
        assert len(messages) == 1
        assert messages[0] == "Valid message"

    def test_add_message_truncation(self, accumulator_with_limits):
        """Test message truncation when exceeding max length."""
        chat_id = 123
        long_message = "This is a very long message that exceeds the limit"

        accumulator_with_limits.add_message(chat_id, long_message)

        messages = accumulator_with_limits.get_messages(chat_id)
        assert len(messages) == 1
        assert len(messages[0]) == 10  # max_message_length
        assert messages[0] == long_message[:10]

    def test_message_limit_enforcement(self, accumulator_with_limits):
        """Test that message count limits are enforced."""
        chat_id = 123

        # Add more messages than the limit (3)
        for i in range(5):
            accumulator_with_limits.add_message(chat_id, f"Message {i}")

        messages = accumulator_with_limits.get_messages(chat_id)
        assert len(messages) == 3  # max_messages_per_chat
        # Should keep the most recent messages
        assert messages == ["Message 2", "Message 3", "Message 4"]

    def test_get_messages_empty_chat(self, accumulator):
        """Test getting messages from a chat with no messages."""
        chat_id = 123
        messages = accumulator.get_messages(chat_id)
        assert messages == []

    def test_get_messages_returns_copy(self, accumulator):
        """Test that get_messages returns a copy, not the original list."""
        chat_id = 123
        accumulator.add_message(chat_id, "Original message")

        messages = accumulator.get_messages(chat_id)
        messages.append("Modified message")

        # Original should be unchanged
        original_messages = accumulator.get_messages(chat_id)
        assert len(original_messages) == 1
        assert original_messages[0] == "Original message"

    def test_get_all_and_clear(self, accumulator):
        """Test getting all messages and clearing the accumulator."""
        chat_id = 123
        test_messages = ["Message 1", "Message 2", "Message 3"]

        for msg in test_messages:
            accumulator.add_message(chat_id, msg)

        # Get all and clear
        retrieved_messages = accumulator.get_all_and_clear(chat_id)

        # Should return all messages
        assert retrieved_messages == test_messages

        # Accumulator should be empty now
        assert accumulator.get_messages(chat_id) == []
        assert accumulator.get_message_count(chat_id) == 0

    def test_get_all_and_clear_empty_chat(self, accumulator):
        """Test get_all_and_clear on empty chat."""
        chat_id = 123
        messages = accumulator.get_all_and_clear(chat_id)
        assert messages == []

    def test_clear_chat(self, accumulator):
        """Test clearing messages for a specific chat."""
        chat1_id = 123
        chat2_id = 456

        accumulator.add_message(chat1_id, "Message for chat 1")
        accumulator.add_message(chat2_id, "Message for chat 2")

        # Clear chat 1
        accumulator.clear_chat(chat1_id)

        # Chat 1 should be empty, chat 2 should be unchanged
        assert accumulator.get_messages(chat1_id) == []
        assert accumulator.get_messages(chat2_id) == ["Message for chat 2"]

    def test_clear_chat_nonexistent(self, accumulator):
        """Test clearing a chat that doesn't exist."""
        chat_id = 123
        # Should not raise an error
        accumulator.clear_chat(chat_id)
        assert accumulator.get_messages(chat_id) == []

    def test_get_message_count(self, accumulator):
        """Test getting message count for a chat."""
        chat_id = 123

        assert accumulator.get_message_count(chat_id) == 0

        accumulator.add_message(chat_id, "Message 1")
        assert accumulator.get_message_count(chat_id) == 1

        accumulator.add_message(chat_id, "Message 2")
        assert accumulator.get_message_count(chat_id) == 2

        accumulator.clear_chat(chat_id)
        assert accumulator.get_message_count(chat_id) == 0

    def test_get_total_chats(self, accumulator):
        """Test getting total number of chats with messages."""
        assert accumulator.get_total_chats() == 0

        accumulator.add_message(123, "Message 1")
        assert accumulator.get_total_chats() == 1

        accumulator.add_message(456, "Message 2")
        assert accumulator.get_total_chats() == 2

        accumulator.add_message(123, "Another message")  # Same chat
        assert accumulator.get_total_chats() == 2

        accumulator.clear_chat(123)
        assert accumulator.get_total_chats() == 1

    def test_get_all_chat_ids(self, accumulator):
        """Test getting all chat IDs with messages."""
        assert accumulator.get_all_chat_ids() == []

        accumulator.add_message(123, "Message 1")
        accumulator.add_message(456, "Message 2")
        accumulator.add_message(789, "Message 3")

        chat_ids = accumulator.get_all_chat_ids()
        assert set(chat_ids) == {123, 456, 789}

        accumulator.clear_chat(456)
        chat_ids = accumulator.get_all_chat_ids()
        assert set(chat_ids) == {123, 789}

    def test_chat_isolation(self, accumulator):
        """Test that messages from different chats are properly isolated."""
        chat1_id = 123
        chat2_id = 456

        # Add messages to both chats
        accumulator.add_message(chat1_id, "Chat 1 Message 1")
        accumulator.add_message(chat2_id, "Chat 2 Message 1")
        accumulator.add_message(chat1_id, "Chat 1 Message 2")
        accumulator.add_message(chat2_id, "Chat 2 Message 2")

        # Verify isolation
        chat1_messages = accumulator.get_messages(chat1_id)
        chat2_messages = accumulator.get_messages(chat2_id)

        assert len(chat1_messages) == 2
        assert len(chat2_messages) == 2
        assert chat1_messages == ["Chat 1 Message 1", "Chat 1 Message 2"]
        assert chat2_messages == ["Chat 2 Message 1", "Chat 2 Message 2"]

        # Clear one chat, other should be unaffected
        accumulator.clear_chat(chat1_id)
        assert accumulator.get_messages(chat1_id) == []
        assert accumulator.get_messages(chat2_id) == ["Chat 2 Message 1", "Chat 2 Message 2"]

    def test_message_order_preservation(self, accumulator):
        """Test that message order is preserved."""
        chat_id = 123
        messages = [f"Message {i}" for i in range(10)]

        for msg in messages:
            accumulator.add_message(chat_id, msg)

        stored_messages = accumulator.get_messages(chat_id)
        assert stored_messages == messages

    def test_limit_enforcement_preserves_order(self, accumulator_with_limits):
        """Test that limit enforcement keeps the most recent messages in order."""
        chat_id = 123

        # Add 5 messages to a limit of 3
        for i in range(5):
            accumulator_with_limits.add_message(chat_id, f"Message {i}")

        messages = accumulator_with_limits.get_messages(chat_id)
        assert len(messages) == 3
        assert messages == ["Message 2", "Message 3", "Message 4"]  # Most recent 3

    def test_edge_case_zero_limits(self):
        """Test behavior with zero limits."""
        accumulator = MessageAccumulator(max_messages_per_chat=0, max_message_length=0)
        chat_id = 123

        accumulator.add_message(chat_id, "Test message")

        # With zero message limit, no messages should be stored
        messages = accumulator.get_messages(chat_id)
        assert messages == []

    def test_edge_case_negative_limits(self):
        """Test behavior with negative limits (should be handled gracefully)."""
        accumulator = MessageAccumulator(max_messages_per_chat=-1, max_message_length=-1)
        chat_id = 123

        # Should not crash, but behavior may vary
        accumulator.add_message(chat_id, "Test message")
        # We don't assert specific behavior for negative limits as it's undefined
