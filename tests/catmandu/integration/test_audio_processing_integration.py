"""Integration tests for audio processing functionality."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from catmandu.core.audio_processor import AudioProcessor
from catmandu.core.config import Settings
from catmandu.core.cost_tracker import CostTracker
from catmandu.core.infrastructure.chat_logger import ChatLogger
from catmandu.core.infrastructure.router import MessageRouter


@pytest.fixture
def mock_logging_service():
    """Create mock logging service."""
    mock = Mock()
    mock.log_chat_interaction_safely = Mock()
    return mock


@pytest.fixture
def audio_settings():
    """Create settings with audio processing enabled."""
    return Settings(
        telegram_bot_token="test_token",
        audio_processing_enabled=True,
        openai_api_key="sk-test_openai_key_for_testing_purposes_only",
        max_audio_file_size_mb=25,
        max_audio_duration_minutes=10,
    )


@pytest.fixture
def mock_telegram_client():
    """Create mock Telegram client."""
    client = AsyncMock()
    client.get_file.return_value = {"file_path": "voice/file_123.ogg"}
    client.download_file.return_value = b"mock_audio_data"
    client.send_chat_action.return_value = None
    return client


@pytest.fixture
def mock_openai_client():
    """Create mock OpenAI client."""
    client = AsyncMock()
    client.transcribe_audio.return_value = {
        "text": "Hello, this is a test transcription.",
        "duration": 2.5,
    }
    client.improve_text.return_value = {
        "text": "Hello, this is an improved test transcription.",
        "usage": {"prompt_tokens": 50, "completion_tokens": 25, "total_tokens": 75},
    }
    return client


@pytest.fixture
def integration_router(audio_settings, mock_telegram_client, mock_openai_client, tmp_path):
    """Create a complete router setup for integration testing."""
    # Create temporary directories
    chat_logs_dir = tmp_path / "chat_logs"
    cost_logs_dir = tmp_path / "cost_logs"
    chat_logs_dir.mkdir()
    cost_logs_dir.mkdir()

    # Update settings with temp directories
    audio_settings.chat_logs_dir = str(chat_logs_dir)
    audio_settings.cost_logs_dir = str(cost_logs_dir)

    # Create real components
    cost_tracker = CostTracker(settings=audio_settings)
    chat_logger = ChatLogger(logs_dir=str(chat_logs_dir))

    # Create logging service
    from catmandu.core.services.logging_service import LoggingService

    logging_service = LoggingService(audio_settings)

    # Create audio processor with mocked OpenAI client
    audio_processor = AudioProcessor(
        settings=audio_settings,
        telegram_client=mock_telegram_client,
        cost_tracker=cost_tracker,
        logging_service=logging_service,
    )

    # Mock the OpenAI client creation
    with patch.object(audio_processor, "_get_openai_client", return_value=mock_openai_client):
        # Create mock services
        mock_mcp_service = AsyncMock()
        mock_registry = MagicMock()
        mock_accumulator_manager = MagicMock()
        mock_accumulator_manager.process_non_command_message.return_value = "📝 Message stored successfully."

        # Create router
        router = MessageRouter(
            mcp_service=mock_mcp_service,
            cattackle_registry=mock_registry,
            accumulator_manager=mock_accumulator_manager,
            chat_logger=chat_logger,
            audio_processor=audio_processor,
            logging_service=logging_service,
        )

        yield router, mock_mcp_service, mock_registry, mock_accumulator_manager


class TestAudioProcessingIntegration:
    """Integration tests for complete audio processing workflow."""

    @pytest.mark.asyncio
    async def test_complete_voice_message_processing_flow(self, integration_router):
        """Test complete end-to-end voice message processing."""
        router, mock_mcp_service, mock_registry, mock_accumulator_manager = integration_router

        # Create a voice message update
        update = {
            "update_id": 123,
            "message": {
                "message_id": 456,
                "from": {"id": 789, "first_name": "Test", "username": "testuser"},
                "chat": {"id": 789, "type": "private"},
                "date": 1234567890,
                "voice": {
                    "file_id": "voice_file_123",
                    "file_unique_id": "unique_123",
                    "duration": 5,
                    "mime_type": "audio/ogg",
                    "file_size": 12345,
                },
            },
        }

        # Process the update
        result = await router.process_update(update)

        # Verify the result
        assert result == (789, "📝 Message stored successfully.")

        # Verify accumulator was called with transcribed text
        mock_accumulator_manager.process_non_command_message.assert_called_once_with(
            789, "Hello, this is an improved test transcription."
        )

    @pytest.mark.asyncio
    async def test_audio_message_becomes_command(self, integration_router):
        """Test audio message that transcribes to a command."""
        router, mock_mcp_service, mock_registry, mock_accumulator_manager = integration_router

        # Mock OpenAI to return a command
        audio_processor = router._audio_processor
        mock_openai_client = await audio_processor._get_openai_client()
        mock_openai_client.transcribe_audio.return_value = {
            "text": "/help",
            "duration": 1.0,
        }
        mock_openai_client.improve_text.return_value = {
            "text": "/help",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }

        # Mock registry and MCP service for command processing
        mock_registry.get_cattackle_for_command.return_value = "test_cattackle"
        mock_mcp_service.execute_cattackle.return_value.data = "Help command executed successfully!"

        # Create audio message update
        update = {
            "update_id": 123,
            "message": {
                "message_id": 456,
                "from": {"id": 789, "first_name": "Test", "username": "testuser"},
                "chat": {"id": 789, "type": "private"},
                "date": 1234567890,
                "audio": {
                    "file_id": "audio_file_123",
                    "file_unique_id": "unique_123",
                    "duration": 3,
                    "mime_type": "audio/mpeg",
                    "file_size": 54321,
                },
            },
        }

        # Process the update
        result = await router.process_update(update)

        # Verify command was executed
        assert result == (789, "Help command executed successfully!")
        mock_mcp_service.execute_cattackle.assert_called_once()

        # Verify accumulator was NOT called (since it was a command)
        mock_accumulator_manager.process_non_command_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_audio_processing_error_handling_integration(self, integration_router):
        """Test error handling in complete integration scenario."""
        router, mock_mcp_service, mock_registry, mock_accumulator_manager = integration_router

        # Mock Telegram client to fail file download
        audio_processor = router._audio_processor
        audio_processor.telegram_client.download_file.return_value = None

        # Create voice message update
        update = {
            "update_id": 123,
            "message": {
                "message_id": 456,
                "from": {"id": 789, "first_name": "Test", "username": "testuser"},
                "chat": {"id": 789, "type": "private"},
                "date": 1234567890,
                "voice": {
                    "file_id": "voice_file_123",
                    "file_unique_id": "unique_123",
                    "duration": 5,
                    "mime_type": "audio/ogg",
                    "file_size": 12345,
                },
            },
        }

        # Process the update
        result = await router.process_update(update)

        # Verify error message is returned
        chat_id, response_text = result
        assert chat_id == 789
        assert "Sorry, I couldn't process the audio message" in response_text

        # Verify accumulator was NOT called due to error
        mock_accumulator_manager.process_non_command_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_cost_tracking_integration(self, integration_router, tmp_path):
        """Test that cost tracking works in complete integration."""
        router, mock_mcp_service, mock_registry, mock_accumulator_manager = integration_router

        # Create voice message update
        update = {
            "update_id": 123,
            "message": {
                "message_id": 456,
                "from": {"id": 789, "first_name": "Test", "username": "testuser"},
                "chat": {"id": 789, "type": "private"},
                "date": 1234567890,
                "voice": {
                    "file_id": "voice_file_123",
                    "file_unique_id": "unique_123",
                    "duration": 5,
                    "mime_type": "audio/ogg",
                    "file_size": 12345,
                },
            },
        }

        # Process the update
        result = await router.process_update(update)

        # Verify processing succeeded
        assert result == (789, "📝 Message stored successfully.")

        # Check that cost log file was created
        cost_logs_dir = tmp_path / "cost_logs"
        cost_log_files = list(cost_logs_dir.glob("*.jsonl"))
        assert len(cost_log_files) > 0

        # Verify cost log content
        with open(cost_log_files[0], "r") as f:
            log_content = f.read()
            assert "whisper_cost" in log_content
            assert "gpt_cost" in log_content
            assert "total_cost" in log_content

    @pytest.mark.asyncio
    async def test_chat_logging_integration(self, integration_router, tmp_path):
        """Test that chat logging works with audio processing."""
        router, mock_mcp_service, mock_registry, mock_accumulator_manager = integration_router

        # Create voice message update
        update = {
            "update_id": 123,
            "message": {
                "message_id": 456,
                "from": {"id": 789, "first_name": "Test", "username": "testuser"},
                "chat": {"id": 789, "type": "private"},
                "date": 1234567890,
                "voice": {
                    "file_id": "voice_file_123",
                    "file_unique_id": "unique_123",
                    "duration": 5,
                    "mime_type": "audio/ogg",
                    "file_size": 12345,
                },
            },
        }

        # Process the update
        result = await router.process_update(update)

        # Verify processing succeeded
        assert result == (789, "📝 Message stored successfully.")

        # Check that chat log file was created
        chat_logs_dir = tmp_path / "chat_logs"
        chat_log_files = list(chat_logs_dir.glob("*.jsonl"))
        assert len(chat_log_files) > 0

        # Verify chat log content includes message metadata
        with open(chat_log_files[0], "r") as f:
            log_content = f.read()
            assert "message" in log_content  # message_type should be "message" for processed audio
            assert "text_length" in log_content
            assert "participant_name" in log_content

    @pytest.mark.asyncio
    async def test_multiple_audio_types_integration(self, integration_router):
        """Test processing different audio message types in integration."""
        router, mock_mcp_service, mock_registry, mock_accumulator_manager = integration_router

        # Test different audio message types
        audio_types = [
            {
                "voice": {
                    "file_id": "voice_123",
                    "file_unique_id": "unique_voice_123",
                    "duration": 3,
                    "mime_type": "audio/ogg",
                    "file_size": 10000,
                }
            },
            {
                "audio": {
                    "file_id": "audio_123",
                    "file_unique_id": "unique_audio_123",
                    "duration": 5,
                    "mime_type": "audio/mpeg",
                    "file_size": 20000,
                }
            },
            {
                "video_note": {
                    "file_id": "video_note_123",
                    "file_unique_id": "unique_video_note_123",
                    "duration": 4,
                    "file_size": 15000,
                }
            },
        ]

        for i, audio_data in enumerate(audio_types):
            update = {
                "update_id": 100 + i,
                "message": {
                    "message_id": 400 + i,
                    "from": {"id": 789, "first_name": "Test", "username": "testuser"},
                    "chat": {"id": 789, "type": "private"},
                    "date": 1234567890 + i,
                    **audio_data,
                },
            }

            # Process each update
            result = await router.process_update(update)

            # Verify each processes successfully
            assert result == (789, "📝 Message stored successfully.")

        # Verify accumulator was called for each message
        assert mock_accumulator_manager.process_non_command_message.call_count == 3
