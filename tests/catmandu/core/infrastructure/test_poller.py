import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, call, patch

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
        # Setup - control the number of iterations before stopping
        call_count = 0
        max_calls = 3

        async def mock_get_updates_controlled(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # After a few calls, trigger stop to prevent infinite loop
            if call_count >= max_calls:
                asyncio.create_task(telegram_poller.stop())
            # Always yield control to event loop
            await asyncio.sleep(0)
            return []

        mock_telegram_client.get_updates.side_effect = mock_get_updates_controlled

        # Execute - run the poller (it will stop itself after max_calls)
        await telegram_poller.run()

        # Verify it stopped and made the expected calls
        assert telegram_poller._should_stop.is_set()
        assert call_count >= max_calls


class TestTelegramPollerBackoff:
    """Test cases for exponential backoff functionality in TelegramPoller."""

    async def test_send_message_with_backoff_success_first_try(self, telegram_poller, mock_telegram_client):
        """Test that successful message sending on first try works correctly."""
        # Setup
        mock_telegram_client.send_message.return_value = {"message_id": 123}

        # Execute
        result = await telegram_poller._send_message_with_backoff(789, "Test message")

        # Verify
        assert result is True
        mock_telegram_client.send_message.assert_called_once_with(789, "Test message")

    @patch("asyncio.sleep")
    async def test_send_message_with_backoff_success_after_retries(
        self, mock_sleep, telegram_poller, mock_telegram_client
    ):
        """Test that message sending succeeds after initial failures."""
        # Setup - fail twice, then succeed
        mock_telegram_client.send_message.side_effect = [
            None,  # First attempt fails
            None,  # Second attempt fails
            {"message_id": 123},  # Third attempt succeeds
        ]

        # Execute
        result = await telegram_poller._send_message_with_backoff(789, "Test message", max_retries=3)

        # Verify
        assert result is True
        assert mock_telegram_client.send_message.call_count == 3
        expected_calls = [call(789, "Test message")] * 3
        mock_telegram_client.send_message.assert_has_calls(expected_calls)
        # Should have slept twice (after first two failures)
        assert mock_sleep.call_count == 2

    @patch("asyncio.sleep")
    async def test_send_message_with_backoff_all_retries_fail(self, mock_sleep, telegram_poller, mock_telegram_client):
        """Test that message sending fails after all retries are exhausted."""
        # Setup - all attempts fail
        mock_telegram_client.send_message.return_value = None

        # Execute
        result = await telegram_poller._send_message_with_backoff(789, "Test message", max_retries=2)

        # Verify
        assert result is False
        assert mock_telegram_client.send_message.call_count == 3  # Initial + 2 retries
        # Should have slept twice (after each failure except the last)
        assert mock_sleep.call_count == 2

    @patch("asyncio.sleep")
    async def test_send_message_with_backoff_timing(self, mock_sleep, telegram_poller, mock_telegram_client):
        """Test that exponential backoff timing works correctly."""
        # Setup - all attempts fail to test timing
        mock_telegram_client.send_message.return_value = None

        # Execute
        result = await telegram_poller._send_message_with_backoff(789, "Test message", max_retries=2, base_delay=0.1)

        # Verify
        assert result is False
        # Should have called sleep twice with exponential backoff
        assert mock_sleep.call_count == 2
        # First delay: base_delay * (2^0) + jitter = 0.1 + [0,1]
        first_delay = mock_sleep.call_args_list[0][0][0]
        assert 0.1 <= first_delay <= 1.1  # 0.1 + jitter [0,1]
        # Second delay: base_delay * (2^1) + jitter = 0.2 + [0,1]
        second_delay = mock_sleep.call_args_list[1][0][0]
        assert 0.2 <= second_delay <= 1.2  # 0.2 + jitter [0,1]

    async def test_send_message_with_backoff_zero_retries(self, telegram_poller, mock_telegram_client):
        """Test that zero retries configuration works correctly."""
        # Setup
        mock_telegram_client.send_message.return_value = None

        # Execute
        result = await telegram_poller._send_message_with_backoff(789, "Test message", max_retries=0)

        # Verify
        assert result is False
        mock_telegram_client.send_message.assert_called_once_with(789, "Test message")

    @patch("asyncio.sleep")
    async def test_run_single_loop_uses_backoff(
        self, mock_sleep, telegram_poller, mock_telegram_client, mock_message_router
    ):
        """Test that _run_single_loop uses the backoff mechanism for sending messages."""
        # Setup
        update = {
            "update_id": 123,
            "message": {
                "chat": {"id": 789},
                "text": "/test",
            },
        }
        mock_telegram_client.get_updates.return_value = [update]
        mock_message_router.process_update.return_value = (789, "Response message")

        # First attempt fails, second succeeds
        mock_telegram_client.send_message.side_effect = [None, {"message_id": 456}]

        # Execute
        await telegram_poller._run_single_loop()

        # Verify that backoff was used (multiple send attempts)
        assert mock_telegram_client.send_message.call_count == 2
        expected_calls = [call(789, "Response message")] * 2
        mock_telegram_client.send_message.assert_has_calls(expected_calls)
        # Should have slept once between attempts
        mock_sleep.assert_called_once()

    @patch("asyncio.sleep")
    async def test_run_single_loop_continues_after_send_failure(
        self, mock_sleep, telegram_poller, mock_telegram_client, mock_message_router
    ):
        """Test that processing continues even if message sending ultimately fails."""
        # Setup - multiple updates, one with failed sending
        updates = [
            {
                "update_id": 123,
                "message": {"chat": {"id": 789}, "text": "/test1"},
            },
            {
                "update_id": 124,
                "message": {"chat": {"id": 789}, "text": "/test2"},
            },
        ]
        mock_telegram_client.get_updates.return_value = updates
        mock_message_router.process_update.side_effect = [
            (789, "Response 1"),
            (789, "Response 2"),
        ]

        # Track call count to handle the backoff retries properly
        call_count = 0

        def mock_send_message(chat_id, text):
            nonlocal call_count
            call_count += 1
            # First message fails all retries (default 3 + initial = 4 attempts)
            if call_count <= 4:
                return None
            # Second message succeeds on first try
            return {"message_id": 456}

        mock_telegram_client.send_message.side_effect = mock_send_message

        # Execute
        await telegram_poller._run_single_loop()

        # Verify both updates were processed despite first send failure
        assert mock_message_router.process_update.call_count == 2
        assert call_count == 5  # 4 failed attempts for first message + 1 success for second
        # Should have slept 3 times (after each failed attempt for first message)
        assert mock_sleep.call_count == 3

    @patch("asyncio.sleep")
    async def test_send_message_with_backoff_custom_parameters(self, mock_sleep, telegram_poller, mock_telegram_client):
        """Test that custom backoff parameters work correctly."""
        # Setup - fail first attempt, succeed second
        mock_telegram_client.send_message.side_effect = [None, {"message_id": 123}]

        # Execute with custom parameters
        result = await telegram_poller._send_message_with_backoff(789, "Test message", max_retries=1, base_delay=0.05)

        # Verify
        assert result is True
        assert mock_telegram_client.send_message.call_count == 2
        # Should have slept once with base_delay of 0.05
        mock_sleep.assert_called_once()
        delay = mock_sleep.call_args[0][0]
        assert 0.05 <= delay <= 1.05  # 0.05 + jitter [0,1]
