"""
Integration tests to verify system commands provide feedback when feedback is disabled.

This test module specifically verifies requirement 1.3 from the message-accumulation-cleanup spec:
"WHEN feedback is disabled THEN no automatic feedback SHALL be provided for message accumulation"
but system commands like /accumulator_status should still work.
"""

from unittest.mock import Mock

import pytest

from catmandu.core.infrastructure.mcp_manager import McpService
from catmandu.core.infrastructure.registry import CattackleRegistry
from catmandu.core.infrastructure.router import MessageRouter
from catmandu.core.services.accumulator import MessageAccumulator
from catmandu.core.services.accumulator_manager import AccumulatorManager


class TestSystemCommandsWithFeedbackDisabled:
    """Test system commands work when feedback is disabled for non-command messages."""

    @pytest.fixture
    def accumulator_manager_feedback_disabled(self):
        """Create AccumulatorManager with feedback disabled (production config)."""
        accumulator = MessageAccumulator(max_messages_per_chat=100, max_message_length=1000)
        return AccumulatorManager(accumulator, feedback_enabled=False)

    @pytest.fixture
    def router_with_feedback_disabled(self, accumulator_manager_feedback_disabled):
        """Create MessageRouter with feedback disabled AccumulatorManager."""
        from catmandu.core.services.chat_logger import ChatLogger

        mock_mcp_service = Mock(spec=McpService)
        mock_registry = Mock(spec=CattackleRegistry)
        mock_chat_logger = Mock(spec=ChatLogger)

        return MessageRouter(
            mcp_service=mock_mcp_service,
            cattackle_registry=mock_registry,
            accumulator_manager=accumulator_manager_feedback_disabled,
            chat_logger=mock_chat_logger,
        )

    @pytest.mark.asyncio
    async def test_non_command_messages_provide_no_feedback_when_disabled(
        self, router_with_feedback_disabled, accumulator_manager_feedback_disabled
    ):
        """Test that non-command messages provide no feedback when feedback is disabled."""
        chat_id = 12345

        # Send non-command messages
        update1 = {"message": {"chat": {"id": chat_id}, "text": "First message"}}
        update2 = {"message": {"chat": {"id": chat_id}, "text": "Second message"}}

        result1 = await router_with_feedback_disabled.process_update(update1)
        result2 = await router_with_feedback_disabled.process_update(update2)

        # Verify no feedback is returned
        assert result1 is None
        assert result2 is None

        # But verify messages were still accumulated
        status = accumulator_manager_feedback_disabled.get_accumulator_status(chat_id)
        assert "2 messages accumulated" in status

    @pytest.mark.asyncio
    async def test_accumulator_status_provides_feedback_when_feedback_disabled(
        self, router_with_feedback_disabled, accumulator_manager_feedback_disabled
    ):
        """Test /accumulator_status still returns status when feedback is disabled."""
        chat_id = 12345

        # Accumulate some messages (no feedback expected)
        accumulator_manager_feedback_disabled.process_non_command_message(chat_id, "Message 1")
        accumulator_manager_feedback_disabled.process_non_command_message(chat_id, "Message 2")

        # Test /accumulator_status command
        status_update = {"message": {"chat": {"id": chat_id}, "text": "/accumulator_status"}}
        result = await router_with_feedback_disabled.process_update(status_update)

        # Verify system command provides feedback
        assert result is not None
        chat_id_result, response = result
        assert chat_id_result == chat_id
        assert "2 messages accumulated" in response
        assert "📝" in response  # Status emoji

    @pytest.mark.asyncio
    async def test_show_accumulator_provides_feedback_when_feedback_disabled(
        self, router_with_feedback_disabled, accumulator_manager_feedback_disabled
    ):
        """Test /show_accumulator still displays messages when feedback is disabled."""
        chat_id = 12345

        # Accumulate some messages (no feedback expected)
        accumulator_manager_feedback_disabled.process_non_command_message(chat_id, "Test message 1")
        accumulator_manager_feedback_disabled.process_non_command_message(chat_id, "Test message 2")

        # Test /show_accumulator command
        show_update = {"message": {"chat": {"id": chat_id}, "text": "/show_accumulator"}}
        result = await router_with_feedback_disabled.process_update(show_update)

        # Verify system command provides feedback
        assert result is not None
        chat_id_result, response = result
        assert chat_id_result == chat_id
        assert "Your accumulated messages (2 total)" in response
        assert "Test message 1" in response
        assert "Test message 2" in response
        assert "📝" in response  # Messages emoji

    @pytest.mark.asyncio
    async def test_clear_accumulator_provides_confirmation_when_feedback_disabled(
        self, router_with_feedback_disabled, accumulator_manager_feedback_disabled
    ):
        """Test /clear_accumulator still provides confirmation when feedback is disabled."""
        chat_id = 12345

        # Accumulate some messages (no feedback expected)
        accumulator_manager_feedback_disabled.process_non_command_message(chat_id, "Message to clear 1")
        accumulator_manager_feedback_disabled.process_non_command_message(chat_id, "Message to clear 2")
        accumulator_manager_feedback_disabled.process_non_command_message(chat_id, "Message to clear 3")

        # Test /clear_accumulator command
        clear_update = {"message": {"chat": {"id": chat_id}, "text": "/clear_accumulator"}}
        result = await router_with_feedback_disabled.process_update(clear_update)

        # Verify system command provides confirmation
        assert result is not None
        chat_id_result, response = result
        assert chat_id_result == chat_id
        assert "Cleared 3 accumulated messages" in response
        assert "🗑️" in response  # Clear emoji

        # Verify accumulator was actually cleared
        status = accumulator_manager_feedback_disabled.get_accumulator_status(chat_id)
        assert "No messages accumulated" in status

    @pytest.mark.asyncio
    async def test_system_commands_work_with_empty_accumulator_when_feedback_disabled(
        self, router_with_feedback_disabled
    ):
        """Test system commands provide appropriate responses for empty accumulator."""
        chat_id = 12345

        # Test /accumulator_status with empty accumulator
        status_update = {"message": {"chat": {"id": chat_id}, "text": "/accumulator_status"}}
        result = await router_with_feedback_disabled.process_update(status_update)

        assert result is not None
        chat_id_result, response = result
        assert chat_id_result == chat_id
        assert "No messages accumulated" in response
        assert "📭" in response  # Empty mailbox emoji

        # Test /show_accumulator with empty accumulator
        show_update = {"message": {"chat": {"id": chat_id}, "text": "/show_accumulator"}}
        result = await router_with_feedback_disabled.process_update(show_update)

        assert result is not None
        chat_id_result, response = result
        assert chat_id_result == chat_id
        assert "No messages accumulated" in response
        assert "📭" in response  # Empty mailbox emoji

        # Test /clear_accumulator with empty accumulator
        clear_update = {"message": {"chat": {"id": chat_id}, "text": "/clear_accumulator"}}
        result = await router_with_feedback_disabled.process_update(clear_update)

        assert result is not None
        chat_id_result, response = result
        assert chat_id_result == chat_id
        assert "No messages to clear" in response
        assert "already empty" in response
        assert "📭" in response  # Empty mailbox emoji

    @pytest.mark.asyncio
    async def test_explicit_user_requests_still_work_when_feedback_disabled(
        self, router_with_feedback_disabled, accumulator_manager_feedback_disabled
    ):
        """Test that explicit user requests for information still work when feedback is disabled."""
        chat_id = 12345

        # Accumulate messages silently
        for i in range(5):
            update = {"message": {"chat": {"id": chat_id}, "text": f"Silent message {i+1}"}}
            result = await router_with_feedback_disabled.process_update(update)
            assert result is None  # No feedback for non-command messages

        # Verify all system commands still provide explicit feedback when requested

        # 1. Status check
        status_update = {"message": {"chat": {"id": chat_id}, "text": "/accumulator_status"}}
        result = await router_with_feedback_disabled.process_update(status_update)
        assert result is not None
        assert "5 messages accumulated" in result[1]

        # 2. Show messages
        show_update = {"message": {"chat": {"id": chat_id}, "text": "/show_accumulator"}}
        result = await router_with_feedback_disabled.process_update(show_update)
        assert result is not None
        assert "Your accumulated messages (5 total)" in result[1]
        assert "Silent message 1" in result[1]
        assert "Silent message 5" in result[1]

        # 3. Clear with confirmation
        clear_update = {"message": {"chat": {"id": chat_id}, "text": "/clear_accumulator"}}
        result = await router_with_feedback_disabled.process_update(clear_update)
        assert result is not None
        assert "Cleared 5 accumulated messages" in result[1]

        # 4. Status check after clear
        status_update = {"message": {"chat": {"id": chat_id}, "text": "/accumulator_status"}}
        result = await router_with_feedback_disabled.process_update(status_update)
        assert result is not None
        assert "No messages accumulated" in result[1]
