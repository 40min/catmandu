import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from catmandu.core.config import Settings
from catmandu.core.infrastructure.poller import TelegramPoller
from catmandu.core.infrastructure.router import MessageRouter
from catmandu.core.models import CattackleResponse
from catmandu.core.services.accumulator import MessageAccumulator
from catmandu.core.services.accumulator_manager import AccumulatorManager

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_telegram_client():
    """Create a mock TelegramClient for integration testing."""
    client = AsyncMock()
    return client


@pytest.fixture
def mock_mcp_service():
    """Create a mock McpService for integration testing."""
    service = AsyncMock()
    service.execute_cattackle.return_value = CattackleResponse(data="test response")
    return service


@pytest.fixture
def real_accumulator_manager():
    """Create a real AccumulatorManager with real MessageAccumulator for integration testing."""
    accumulator = MessageAccumulator(max_messages_per_chat=100, max_message_length=1000)
    return AccumulatorManager(accumulator, feedback_enabled=False)


@pytest.fixture
def temp_settings():
    """Create settings with a temporary file for offset storage."""
    with tempfile.TemporaryDirectory() as temp_dir:
        settings = Settings()
        settings.update_id_file_path = str(Path(temp_dir) / "update_id.txt")
        yield settings


@pytest.fixture
def integration_poller(
    mock_telegram_client,
    mock_mcp_service,
    test_registry_with_cattackles,
    real_accumulator_manager,
    temp_settings,
):
    """Create a TelegramPoller with real components for integration testing."""
    from unittest.mock import MagicMock

    from catmandu.core.services.chat_logger import ChatLogger

    mock_chat_logger = MagicMock(spec=ChatLogger)
    message_router = MessageRouter(
        mcp_service=mock_mcp_service,
        cattackle_registry=test_registry_with_cattackles,
        accumulator_manager=real_accumulator_manager,
        chat_logger=mock_chat_logger,
    )

    return TelegramPoller(
        router=message_router,
        telegram_client=mock_telegram_client,
        settings=temp_settings,
    )


class TestTelegramToAccumulatorFlow:
    """Integration tests for complete message flow from Telegram to accumulator."""

    async def test_non_command_message_accumulation_flow(
        self, integration_poller, mock_telegram_client, real_accumulator_manager
    ):
        """Test that non-command messages flow from Telegram through poller to accumulator."""
        # Setup: Non-command message from Telegram
        updates = [
            {
                "update_id": 200,
                "message": {
                    "message_id": 500,
                    "chat": {"id": 12345, "type": "private"},
                    "text": "This is a test message for accumulation",
                },
            }
        ]
        mock_telegram_client.get_updates.return_value = updates

        # Execute: Process the update through the poller
        await integration_poller._run_single_loop()

        # Verify: Message was accumulated
        accumulated_messages = real_accumulator_manager._accumulator.get_messages(12345)
        assert len(accumulated_messages) == 1
        assert accumulated_messages[0] == "This is a test message for accumulation"

        # Verify: No feedback was sent to user (feedback_enabled=False)
        mock_telegram_client.send_message.assert_not_called()

    async def test_multiple_message_accumulation_flow(
        self, integration_poller, mock_telegram_client, real_accumulator_manager
    ):
        """Test that multiple non-command messages are accumulated in order."""
        # Setup: Multiple non-command messages
        updates = [
            {
                "update_id": 201,
                "message": {
                    "message_id": 501,
                    "chat": {"id": 12345, "type": "private"},
                    "text": "First message",
                },
            },
            {
                "update_id": 202,
                "message": {
                    "message_id": 502,
                    "chat": {"id": 12345, "type": "private"},
                    "text": "Second message",
                },
            },
            {
                "update_id": 203,
                "message": {
                    "message_id": 503,
                    "chat": {"id": 12345, "type": "private"},
                    "text": "Third message",
                },
            },
        ]
        mock_telegram_client.get_updates.return_value = updates

        # Execute: Process all updates
        await integration_poller._run_single_loop()

        # Verify: All messages were accumulated in order
        accumulated_messages = real_accumulator_manager._accumulator.get_messages(12345)
        assert len(accumulated_messages) == 3
        assert accumulated_messages[0] == "First message"
        assert accumulated_messages[1] == "Second message"
        assert accumulated_messages[2] == "Third message"

        # Verify: No feedback was sent for non-command messages (feedback_enabled=False)
        assert mock_telegram_client.send_message.call_count == 0

    async def test_command_execution_with_accumulated_parameters_flow(
        self, integration_poller, mock_telegram_client, mock_mcp_service, real_accumulator_manager
    ):
        """Test complete flow: accumulate messages, then execute command with accumulated parameters."""
        # Setup: First accumulate some messages
        accumulation_updates = [
            {
                "update_id": 204,
                "message": {
                    "message_id": 504,
                    "chat": {"id": 12345, "type": "private"},
                    "text": "Parameter 1",
                },
            },
            {
                "update_id": 205,
                "message": {
                    "message_id": 505,
                    "chat": {"id": 12345, "type": "private"},
                    "text": "Parameter 2",
                },
            },
        ]
        mock_telegram_client.get_updates.return_value = accumulation_updates
        await integration_poller._run_single_loop()

        # Verify messages were accumulated
        accumulated_messages = real_accumulator_manager._accumulator.get_messages(12345)
        assert len(accumulated_messages) == 2

        # Setup: Now execute a command
        command_updates = [
            {
                "update_id": 206,
                "message": {
                    "message_id": 506,
                    "chat": {"id": 12345, "type": "private"},
                    "text": "/echo Execute with accumulated params",
                },
            }
        ]
        mock_telegram_client.get_updates.return_value = command_updates

        # Execute: Process the command
        await integration_poller._run_single_loop()

        # Verify: Command was executed with accumulated parameters
        mock_mcp_service.execute_cattackle.assert_called_once()
        call_args = mock_mcp_service.execute_cattackle.call_args
        payload = call_args.kwargs["payload"]
        assert payload["accumulated_params"] == ["Parameter 1", "Parameter 2"]
        assert payload["text"] == "Execute with accumulated params"
        assert len(payload) == 2  # Only text and accumulated_params
        assert "message" not in payload  # Verify simplified payload structure

        # Verify: Accumulator was cleared after command execution
        remaining_messages = real_accumulator_manager._accumulator.get_messages(12345)
        assert len(remaining_messages) == 0

        # Verify: Command response was sent
        mock_telegram_client.send_message.assert_called_with(12345, "test response")

    async def test_chat_isolation_in_message_flow(
        self, integration_poller, mock_telegram_client, real_accumulator_manager
    ):
        """Test that messages from different chats are isolated in the accumulator."""
        # Setup: Messages from two different chats
        updates = [
            {
                "update_id": 207,
                "message": {
                    "message_id": 507,
                    "chat": {"id": 11111, "type": "private"},
                    "text": "Message for chat 1",
                },
            },
            {
                "update_id": 208,
                "message": {
                    "message_id": 508,
                    "chat": {"id": 22222, "type": "private"},
                    "text": "Message for chat 2",
                },
            },
            {
                "update_id": 209,
                "message": {
                    "message_id": 509,
                    "chat": {"id": 11111, "type": "private"},
                    "text": "Another message for chat 1",
                },
            },
        ]
        mock_telegram_client.get_updates.return_value = updates

        # Execute: Process all updates
        await integration_poller._run_single_loop()

        # Verify: Messages are isolated by chat
        chat1_messages = real_accumulator_manager._accumulator.get_messages(11111)
        chat2_messages = real_accumulator_manager._accumulator.get_messages(22222)

        assert len(chat1_messages) == 2
        assert chat1_messages[0] == "Message for chat 1"
        assert chat1_messages[1] == "Another message for chat 1"

        assert len(chat2_messages) == 1
        assert chat2_messages[0] == "Message for chat 2"

    async def test_system_commands_flow(self, integration_poller, mock_telegram_client, real_accumulator_manager):
        """Test that system commands work correctly in the complete flow."""
        # Setup: First accumulate a message
        accumulation_updates = [
            {
                "update_id": 210,
                "message": {
                    "message_id": 510,
                    "chat": {"id": 12345, "type": "private"},
                    "text": "Test message for system commands",
                },
            }
        ]
        mock_telegram_client.get_updates.return_value = accumulation_updates
        await integration_poller._run_single_loop()

        # Verify message was accumulated
        accumulated_messages = real_accumulator_manager._accumulator.get_messages(12345)
        assert len(accumulated_messages) == 1

        # Setup: Execute system command to show accumulator
        system_command_updates = [
            {
                "update_id": 211,
                "message": {
                    "message_id": 511,
                    "chat": {"id": 12345, "type": "private"},
                    "text": "/show_accumulator",
                },
            }
        ]
        mock_telegram_client.get_updates.return_value = system_command_updates

        # Execute: Process the system command
        await integration_poller._run_single_loop()

        # Verify: System command response was sent
        mock_telegram_client.send_message.assert_called()
        call_args = mock_telegram_client.send_message.call_args
        assert call_args[0][0] == 12345  # chat_id
        response_text = call_args[0][1]
        assert "Test message for system commands" in response_text

        # Verify: Accumulator still contains the message (show doesn't clear)
        remaining_messages = real_accumulator_manager._accumulator.get_messages(12345)
        assert len(remaining_messages) == 1

    async def test_mixed_updates_with_non_message_updates(
        self, integration_poller, mock_telegram_client, real_accumulator_manager
    ):
        """Test that the flow handles mixed update types including non-message updates."""
        # Setup: Mix of message and non-message updates
        updates = [
            {
                "update_id": 212,
                "callback_query": {  # Non-message update
                    "id": "callback123",
                    "from": {"id": 12345},
                    "data": "some_callback_data",
                },
            },
            {
                "update_id": 213,
                "message": {
                    "message_id": 512,
                    "chat": {"id": 12345, "type": "private"},
                    "text": "Regular message",
                },
            },
            {
                "update_id": 214,
                "edited_message": {  # Non-message update
                    "message_id": 513,
                    "chat": {"id": 12345, "type": "private"},
                    "text": "Edited message",
                },
            },
        ]
        mock_telegram_client.get_updates.return_value = updates

        # Execute: Process all updates
        await integration_poller._run_single_loop()

        # Verify: Only the regular message was accumulated
        accumulated_messages = real_accumulator_manager._accumulator.get_messages(12345)
        assert len(accumulated_messages) == 1
        assert accumulated_messages[0] == "Regular message"

        # Verify: No feedback was sent for non-command messages (feedback_enabled=False)
        assert mock_telegram_client.send_message.call_count == 0

    async def test_empty_and_whitespace_message_handling(
        self, integration_poller, mock_telegram_client, real_accumulator_manager
    ):
        """Test that empty and whitespace-only messages are handled correctly."""
        # Setup: Messages with various empty/whitespace content
        updates = [
            {
                "update_id": 215,
                "message": {
                    "message_id": 514,
                    "chat": {"id": 12345, "type": "private"},
                    "text": "",  # Empty message
                },
            },
            {
                "update_id": 216,
                "message": {
                    "message_id": 515,
                    "chat": {"id": 12345, "type": "private"},
                    "text": "   ",  # Whitespace only
                },
            },
            {
                "update_id": 217,
                "message": {
                    "message_id": 516,
                    "chat": {"id": 12345, "type": "private"},
                    "text": "Valid message",  # Valid message
                },
            },
        ]
        mock_telegram_client.get_updates.return_value = updates

        # Execute: Process all updates
        await integration_poller._run_single_loop()

        # Verify: Only the valid message was accumulated (empty/whitespace filtered by AccumulatorManager)
        accumulated_messages = real_accumulator_manager._accumulator.get_messages(12345)
        assert len(accumulated_messages) == 1
        assert accumulated_messages[0] == "Valid message"

        # Verify: No feedback was sent for non-command messages (feedback_enabled=False)
        assert mock_telegram_client.send_message.call_count == 0
