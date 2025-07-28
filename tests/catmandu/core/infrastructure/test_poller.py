import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from catmandu.core.config import Settings
from catmandu.core.infrastructure.poller import TelegramPoller

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_telegram_client():
    """Create a mock TelegramClient."""
    client = AsyncMock()
    return client


@pytest.fixture
def mock_message_router():
    """Create a mock MessageRouter."""
    router = AsyncMock()
    return router


@pytest.fixture
def temp_settings():
    """Create settings with a temporary file for offset storage."""
    with tempfile.TemporaryDirectory() as temp_dir:
        settings = Settings()
        settings.update_id_file_path = str(Path(temp_dir) / "update_id.txt")
        yield settings


@pytest.fixture
def telegram_poller(mock_message_router, mock_telegram_client, temp_settings):
    """Create a TelegramPoller instance for testing."""
    return TelegramPoller(
        router=mock_message_router,
        telegram_client=mock_telegram_client,
        settings=temp_settings,
    )


class TestTelegramPoller:
    """Test cases for TelegramPoller service."""

    async def test_processes_command_messages(self, telegram_poller, mock_telegram_client, mock_message_router):
        """Test that TelegramPoller processes command messages correctly."""
        # Setup
        command_update = {
            "update_id": 123,
            "message": {
                "message_id": 456,
                "chat": {"id": 789, "type": "private"},
                "text": "/echo Hello World",
            },
        }
        mock_telegram_client.get_updates.return_value = [command_update]
        mock_message_router.process_update.return_value = (789, "Echo: Hello World")

        # Execute
        await telegram_poller._run_single_loop()

        # Verify
        mock_telegram_client.get_updates.assert_called_once()
        mock_message_router.process_update.assert_called_once_with(command_update)
        mock_telegram_client.send_message.assert_called_once_with(789, "Echo: Hello World")

    async def test_processes_non_command_messages(self, telegram_poller, mock_telegram_client, mock_message_router):
        """Test that TelegramPoller processes non-command messages correctly."""
        # Setup
        non_command_update = {
            "update_id": 124,
            "message": {
                "message_id": 457,
                "chat": {"id": 789, "type": "private"},
                "text": "This is a regular message",
            },
        }
        mock_telegram_client.get_updates.return_value = [non_command_update]
        mock_message_router.process_update.return_value = (789, "📝 Message stored for your next command.")

        # Execute
        await telegram_poller._run_single_loop()

        # Verify
        mock_telegram_client.get_updates.assert_called_once()
        mock_message_router.process_update.assert_called_once_with(non_command_update)
        mock_telegram_client.send_message.assert_called_once_with(789, "📝 Message stored for your next command.")

    async def test_processes_non_command_messages_without_response(
        self, telegram_poller, mock_telegram_client, mock_message_router
    ):
        """Test that TelegramPoller handles non-command messages that don't generate responses."""
        # Setup
        non_command_update = {
            "update_id": 125,
            "message": {
                "message_id": 458,
                "chat": {"id": 789, "type": "private"},
                "text": "Silent message",
            },
        }
        mock_telegram_client.get_updates.return_value = [non_command_update]
        mock_message_router.process_update.return_value = None  # No response

        # Execute
        await telegram_poller._run_single_loop()

        # Verify
        mock_telegram_client.get_updates.assert_called_once()
        mock_message_router.process_update.assert_called_once_with(non_command_update)
        mock_telegram_client.send_message.assert_not_called()

    async def test_processes_mixed_message_types(self, telegram_poller, mock_telegram_client, mock_message_router):
        """Test that TelegramPoller processes both command and non-command messages in sequence."""
        # Setup
        updates = [
            {
                "update_id": 126,
                "message": {
                    "message_id": 459,
                    "chat": {"id": 789, "type": "private"},
                    "text": "First message",
                },
            },
            {
                "update_id": 127,
                "message": {
                    "message_id": 460,
                    "chat": {"id": 789, "type": "private"},
                    "text": "Second message",
                },
            },
            {
                "update_id": 128,
                "message": {
                    "message_id": 461,
                    "chat": {"id": 789, "type": "private"},
                    "text": "/echo Execute command",
                },
            },
        ]
        mock_telegram_client.get_updates.return_value = updates
        mock_message_router.process_update.side_effect = [
            (789, "📝 Message 1 stored"),  # Non-command response
            None,  # Non-command no response
            (789, "Echo: Execute command"),  # Command response
        ]

        # Execute
        await telegram_poller._run_single_loop()

        # Verify
        mock_telegram_client.get_updates.assert_called_once()
        assert mock_message_router.process_update.call_count == 3
        assert mock_telegram_client.send_message.call_count == 2
        mock_telegram_client.send_message.assert_any_call(789, "📝 Message 1 stored")
        mock_telegram_client.send_message.assert_any_call(789, "Echo: Execute command")

    async def test_offset_management(self, telegram_poller, mock_telegram_client, mock_message_router, temp_settings):
        """Test that TelegramPoller correctly manages update offsets."""
        # Setup
        updates = [
            {"update_id": 100, "message": {"chat": {"id": 789}, "text": "/test"}},
            {"update_id": 101, "message": {"chat": {"id": 789}, "text": "message"}},
        ]
        mock_telegram_client.get_updates.return_value = updates
        mock_message_router.process_update.return_value = None

        # Execute
        await telegram_poller._run_single_loop()

        # Verify offset is saved
        offset_file = Path(temp_settings.update_id_file_path)
        assert offset_file.exists()
        assert offset_file.read_text().strip() == "102"  # Last update_id + 1

    async def test_handles_empty_updates(self, telegram_poller, mock_telegram_client, mock_message_router):
        """Test that TelegramPoller handles empty update lists correctly."""
        # Setup
        mock_telegram_client.get_updates.return_value = []

        # Execute
        await telegram_poller._run_single_loop()

        # Verify
        mock_telegram_client.get_updates.assert_called_once()
        mock_message_router.process_update.assert_not_called()
        mock_telegram_client.send_message.assert_not_called()

    async def test_handles_updates_without_message(self, telegram_poller, mock_telegram_client, mock_message_router):
        """Test that TelegramPoller handles updates that don't contain messages."""
        # Setup
        updates = [
            {"update_id": 130},  # Update without message
            {
                "update_id": 131,
                "message": {
                    "chat": {"id": 789},
                    "text": "/test",
                },
            },
        ]
        mock_telegram_client.get_updates.return_value = updates
        mock_message_router.process_update.side_effect = [None, (789, "Response")]

        # Execute
        await telegram_poller._run_single_loop()

        # Verify both updates are processed
        assert mock_message_router.process_update.call_count == 2
        mock_telegram_client.send_message.assert_called_once_with(789, "Response")

    async def test_stop_functionality(self, telegram_poller, mock_telegram_client, mock_message_router):
        """Test that TelegramPoller stops correctly when stop() is called."""
        # Setup - make get_updates simulate the real behavior with a delay
        call_count = 0

        async def mock_get_updates_with_realistic_behavior(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # Simulate the timeout behavior of real Telegram API
            await asyncio.sleep(0.01)  # Small delay to simulate network call
            return []

        mock_telegram_client.get_updates.side_effect = mock_get_updates_with_realistic_behavior

        # Start the poller in a task
        poller_task = asyncio.create_task(telegram_poller.run())

        # Let it run briefly to ensure it's started and makes at least one call
        await asyncio.sleep(0.05)

        # Verify it's running (made at least one call)
        assert call_count > 0

        # Stop the poller
        await telegram_poller.stop()

        # Wait for the task to complete with a timeout
        try:
            await asyncio.wait_for(poller_task, timeout=1.0)
        except asyncio.TimeoutError:
            poller_task.cancel()
            pytest.fail("Poller did not stop within timeout")

        # Verify it stopped
        assert telegram_poller._should_stop.is_set()
