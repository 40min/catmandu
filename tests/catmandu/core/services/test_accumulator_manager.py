import pytest

from catmandu.core.services.accumulator import MessageAccumulator
from catmandu.core.services.accumulator_manager import AccumulatorManager


class TestAccumulatorManager:
    """Test cases for AccumulatorManager service."""

    @pytest.fixture
    def accumulator(self):
        """Create a MessageAccumulator instance for testing."""
        return MessageAccumulator(max_messages_per_chat=5, max_message_length=100)

    @pytest.fixture
    def manager(self, accumulator):
        """Create an AccumulatorManager instance for testing."""
        return AccumulatorManager(accumulator, feedback_enabled=True)

    @pytest.fixture
    def manager_no_feedback(self, accumulator):
        """Create an AccumulatorManager instance with feedback disabled."""
        return AccumulatorManager(accumulator, feedback_enabled=False)

    def test_init(self, accumulator):
        """Test AccumulatorManager initialization."""
        manager = AccumulatorManager(accumulator, feedback_enabled=True)
        assert manager._accumulator is accumulator
        assert manager._feedback_enabled is True

        manager_no_feedback = AccumulatorManager(accumulator, feedback_enabled=False)
        assert manager_no_feedback._feedback_enabled is False

    def test_init_default_feedback_disabled(self, accumulator):
        """Test AccumulatorManager initialization with default feedback disabled."""
        manager = AccumulatorManager(accumulator)
        assert manager._accumulator is accumulator
        assert manager._feedback_enabled is False

    def test_process_non_command_message_with_feedback(self, manager):
        """Test processing non-command messages with feedback enabled."""
        chat_id = 12345

        # First message
        feedback = manager.process_non_command_message(chat_id, "Hello world")
        assert feedback == "📝 Message stored. You now have 1 message ready for your next command."

        # Second message
        feedback = manager.process_non_command_message(chat_id, "Another message")
        assert feedback == "📝 Message stored. You now have 2 messages ready for your next command."

        # Verify messages were stored
        messages = manager._accumulator.get_messages(chat_id)
        assert messages == ["Hello world", "Another message"]

    def test_process_non_command_message_without_feedback(self, manager_no_feedback):
        """Test processing non-command messages with feedback disabled."""
        chat_id = 12345

        feedback = manager_no_feedback.process_non_command_message(chat_id, "Hello world")
        assert feedback is None

        # Verify message was still stored
        messages = manager_no_feedback._accumulator.get_messages(chat_id)
        assert messages == ["Hello world"]

    def test_process_non_command_message_default_no_feedback(self, accumulator):
        """Test processing non-command messages with default constructor (feedback disabled)."""
        manager = AccumulatorManager(accumulator)  # Using default feedback_enabled=False
        chat_id = 12345

        # First message
        feedback = manager.process_non_command_message(chat_id, "Hello world")
        assert feedback is None

        # Second message
        feedback = manager.process_non_command_message(chat_id, "Another message")
        assert feedback is None

        # Verify messages were still stored
        messages = manager._accumulator.get_messages(chat_id)
        assert messages == ["Hello world", "Another message"]

    def test_process_non_command_message_empty_text(self, manager):
        """Test processing empty or whitespace-only messages."""
        chat_id = 12345

        # Empty string
        feedback = manager.process_non_command_message(chat_id, "")
        assert feedback is None  # No feedback for empty messages

        # Whitespace only
        feedback = manager.process_non_command_message(chat_id, "   ")
        assert feedback is None

        # Verify no messages were stored
        messages = manager._accumulator.get_messages(chat_id)
        assert messages == []

    def test_get_all_parameters_and_clear(self, manager):
        """Test getting all parameters and clearing accumulator atomically."""
        chat_id = 12345

        # Add some messages
        manager.process_non_command_message(chat_id, "First message")
        manager.process_non_command_message(chat_id, "Second message")
        manager.process_non_command_message(chat_id, "Third message")

        # Get all parameters and clear
        parameters = manager.get_all_parameters_and_clear(chat_id)
        assert parameters == ["First message", "Second message", "Third message"]

        # Verify accumulator was cleared
        remaining_messages = manager._accumulator.get_messages(chat_id)
        assert remaining_messages == []

    def test_get_all_parameters_and_clear_empty(self, manager):
        """Test getting parameters when accumulator is empty."""
        chat_id = 12345

        parameters = manager.get_all_parameters_and_clear(chat_id)
        assert parameters == []

    def test_get_accumulator_status(self, manager):
        """Test getting accumulator status."""
        chat_id = 12345

        # Empty accumulator
        status = manager.get_accumulator_status(chat_id)
        assert status == "📭 No messages accumulated. Send some messages and then use a command!"

        # One message
        manager.process_non_command_message(chat_id, "Single message")
        status = manager.get_accumulator_status(chat_id)
        assert status == "📝 You have 1 message accumulated and ready for your next command."

        # Multiple messages
        manager.process_non_command_message(chat_id, "Second message")
        manager.process_non_command_message(chat_id, "Third message")
        status = manager.get_accumulator_status(chat_id)
        assert status == "📝 You have 3 messages accumulated and ready for your next command."

    def test_show_accumulated_messages(self, manager):
        """Test showing accumulated messages."""
        chat_id = 12345

        # Empty accumulator
        display = manager.show_accumulated_messages(chat_id)
        assert display == "📭 No messages accumulated."

        # Add some messages
        manager.process_non_command_message(chat_id, "First message")
        manager.process_non_command_message(chat_id, "Second message")

        display = manager.show_accumulated_messages(chat_id)
        expected = "📝 Your accumulated messages (2 total):\n" "1. First message\n" "2. Second message"
        assert display == expected

    def test_show_accumulated_messages_long_message(self, manager):
        """Test showing accumulated messages with long message truncation."""
        chat_id = 12345

        # Add a long message (will be truncated by MessageAccumulator to 100 chars)
        long_message = "A" * 150  # Longer than 100 character limit in accumulator
        manager.process_non_command_message(chat_id, long_message)

        display = manager.show_accumulated_messages(chat_id)
        # MessageAccumulator truncates to 100 chars, so no additional "..." needed
        expected = "📝 Your accumulated messages (1 total):\n" f"1. {'A' * 100}"
        assert display == expected

    def test_show_accumulated_messages_display_truncation(self):
        """Test display truncation when accumulator allows longer messages."""
        # Create accumulator with higher message length limit
        accumulator = MessageAccumulator(max_messages_per_chat=5, max_message_length=200)
        manager = AccumulatorManager(accumulator, feedback_enabled=True)
        chat_id = 12345

        # Add a message longer than display limit (100) but shorter than accumulator limit (200)
        long_message = "B" * 150
        manager.process_non_command_message(chat_id, long_message)

        display = manager.show_accumulated_messages(chat_id)
        # Should be truncated for display purposes
        expected = "📝 Your accumulated messages (1 total):\n" f"1. {'B' * 100}..."
        assert display == expected

    def test_clear_accumulator(self, manager):
        """Test clearing accumulator manually."""
        chat_id = 12345

        # Clear empty accumulator
        result = manager.clear_accumulator(chat_id)
        assert result == "📭 No messages to clear - your accumulator is already empty."

        # Add one message and clear
        manager.process_non_command_message(chat_id, "Single message")
        result = manager.clear_accumulator(chat_id)
        assert result == "🗑️ Cleared 1 accumulated message."

        # Verify it was cleared
        messages = manager._accumulator.get_messages(chat_id)
        assert messages == []

        # Add multiple messages and clear
        manager.process_non_command_message(chat_id, "First")
        manager.process_non_command_message(chat_id, "Second")
        manager.process_non_command_message(chat_id, "Third")
        result = manager.clear_accumulator(chat_id)
        assert result == "🗑️ Cleared 3 accumulated messages."

    def test_get_global_status(self, manager):
        """Test getting global accumulator status."""
        # Empty state
        status = manager.get_global_status()
        assert status == "📊 Global Status: No active chat accumulators."

        # Add messages to multiple chats
        manager.process_non_command_message(12345, "Message 1")
        manager.process_non_command_message(12345, "Message 2")
        manager.process_non_command_message(67890, "Message 3")

        status = manager.get_global_status()
        assert status == "📊 Global Status: 2 active chat(s) with 3 total accumulated message(s)."

    def test_chat_isolation(self, manager):
        """Test that different chats are isolated."""
        chat_id_1 = 12345
        chat_id_2 = 67890

        # Add messages to different chats
        manager.process_non_command_message(chat_id_1, "Chat 1 message 1")
        manager.process_non_command_message(chat_id_1, "Chat 1 message 2")
        manager.process_non_command_message(chat_id_2, "Chat 2 message 1")

        # Verify isolation
        chat_1_messages = manager._accumulator.get_messages(chat_id_1)
        chat_2_messages = manager._accumulator.get_messages(chat_id_2)

        assert chat_1_messages == ["Chat 1 message 1", "Chat 1 message 2"]
        assert chat_2_messages == ["Chat 2 message 1"]

        # Clear one chat shouldn't affect the other
        manager.clear_accumulator(chat_id_1)

        assert manager._accumulator.get_messages(chat_id_1) == []
        assert manager._accumulator.get_messages(chat_id_2) == ["Chat 2 message 1"]

    def test_parameter_extraction_order(self, manager):
        """Test that parameters are extracted in the correct order."""
        chat_id = 12345

        # Add messages in specific order
        messages = ["First", "Second", "Third", "Fourth"]
        for message in messages:
            manager.process_non_command_message(chat_id, message)

        # Extract parameters
        parameters = manager.get_all_parameters_and_clear(chat_id)
        assert parameters == messages

    def test_edge_case_multiple_clears(self, manager):
        """Test multiple consecutive clears."""
        chat_id = 12345

        # Add messages
        manager.process_non_command_message(chat_id, "Message 1")
        manager.process_non_command_message(chat_id, "Message 2")

        # First clear
        result1 = manager.clear_accumulator(chat_id)
        assert result1 == "🗑️ Cleared 2 accumulated messages."

        # Second clear (should be empty)
        result2 = manager.clear_accumulator(chat_id)
        assert result2 == "📭 No messages to clear - your accumulator is already empty."

    def test_edge_case_parameter_extraction_after_clear(self, manager):
        """Test parameter extraction after manual clear."""
        chat_id = 12345

        # Add messages and clear manually
        manager.process_non_command_message(chat_id, "Message 1")
        manager.clear_accumulator(chat_id)

        # Try to extract parameters
        parameters = manager.get_all_parameters_and_clear(chat_id)
        assert parameters == []

    def test_memory_limit_enforcement(self, manager):
        """Test that memory limits are enforced through the manager."""
        chat_id = 12345

        # Add more messages than the limit (accumulator has max_messages_per_chat=5)
        for i in range(7):
            manager.process_non_command_message(chat_id, f"Message {i+1}")

        # Should only have the last 5 messages
        messages = manager._accumulator.get_messages(chat_id)
        assert len(messages) == 5
        assert messages == ["Message 3", "Message 4", "Message 5", "Message 6", "Message 7"]

        # Status should reflect the correct count
        status = manager.get_accumulator_status(chat_id)
        assert status == "📝 You have 5 messages accumulated and ready for your next command."
