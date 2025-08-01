"""Tests for MessageRouter audio processing functionality."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from catmandu.core.audio_processor import AudioProcessingError, AudioProcessor
from catmandu.core.infrastructure.mcp_manager import McpService
from catmandu.core.infrastructure.registry import CattackleRegistry
from catmandu.core.infrastructure.router import MessageRouter
from catmandu.core.models import CattackleConfig, CommandsConfig, McpConfig, StdioTransportConfig
from catmandu.core.services.accumulator import MessageAccumulator
from catmandu.core.services.accumulator_manager import AccumulatorManager


@pytest.fixture
def mock_mcp_service():
    """Create a mock MCP service."""
    service = AsyncMock(spec=McpService)
    mock_response = MagicMock()
    mock_response.data = {"result": "test response"}
    service.execute_cattackle.return_value = mock_response
    return service


@pytest.fixture
def mock_registry():
    """Create a mock registry with test cattackles."""
    registry = MagicMock(spec=CattackleRegistry)

    # Create test cattackle configs
    echo_config = CattackleConfig(
        name="echo",
        version="0.1.0",
        description="Echo cattackle",
        commands={"echo": CommandsConfig(description="Echo command")},
        mcp=McpConfig(
            transport=StdioTransportConfig(type="stdio", command="python"),
            timeout=30.0,
            max_retries=3,
        ),
    )

    # Configure mock methods
    def find_by_cattackle_and_command(cattackle_name, command):
        if cattackle_name == "echo" and command == "echo":
            return echo_config
        return None

    def find_by_command(command):
        if command == "echo":
            return echo_config
        return None

    registry.find_by_cattackle_and_command.side_effect = find_by_cattackle_and_command
    registry.find_by_command.side_effect = find_by_command

    return registry


@pytest.fixture
def accumulator_manager():
    """Create a real AccumulatorManager with feedback enabled for testing."""
    accumulator = MessageAccumulator(max_messages_per_chat=100, max_message_length=1000)
    return AccumulatorManager(accumulator, feedback_enabled=True)


@pytest.fixture
def accumulator_manager_no_feedback():
    """Create a real AccumulatorManager with feedback disabled for testing."""
    accumulator = MessageAccumulator(max_messages_per_chat=100, max_message_length=1000)
    return AccumulatorManager(accumulator, feedback_enabled=False)


@pytest.fixture
def mock_chat_logger():
    """Create a mock chat logger."""
    from catmandu.core.infrastructure.chat_logger import ChatLogger

    return MagicMock(spec=ChatLogger)


@pytest.fixture
def mock_audio_processor():
    """Create a mock audio processor."""
    processor = AsyncMock(spec=AudioProcessor)
    processor.telegram_client = AsyncMock()
    processor.telegram_client.send_chat_action = AsyncMock(return_value=True)

    # Mock successful processing by default
    processor.process_audio_message = AsyncMock(return_value="Hello world")

    return processor


@pytest.fixture
def router_with_audio(mock_mcp_service, mock_registry, accumulator_manager, mock_chat_logger, mock_audio_processor):
    """Create a router with audio processing enabled."""
    return MessageRouter(
        mcp_service=mock_mcp_service,
        cattackle_registry=mock_registry,
        accumulator_manager=accumulator_manager,
        chat_logger=mock_chat_logger,
        audio_processor=mock_audio_processor,
    )


@pytest.fixture
def router_with_audio_no_feedback(
    mock_mcp_service, mock_registry, accumulator_manager_no_feedback, mock_chat_logger, mock_audio_processor
):
    """Create a router with audio processing enabled and no accumulator feedback."""
    return MessageRouter(
        mcp_service=mock_mcp_service,
        cattackle_registry=mock_registry,
        accumulator_manager=accumulator_manager_no_feedback,
        chat_logger=mock_chat_logger,
        audio_processor=mock_audio_processor,
    )


@pytest.fixture
def router_no_audio(mock_mcp_service, mock_registry, accumulator_manager, mock_chat_logger):
    """Create a router without audio processing."""
    return MessageRouter(
        mcp_service=mock_mcp_service,
        cattackle_registry=mock_registry,
        accumulator_manager=accumulator_manager,
        chat_logger=mock_chat_logger,
        audio_processor=None,
    )


@pytest.mark.asyncio
async def test_process_audio_message_voice_success(router_with_audio, mock_audio_processor, mock_chat_logger):
    """Test successful processing of voice message."""
    update = {
        "message": {
            "chat": {"id": 123},
            "from": {"id": 456, "username": "testuser"},
            "voice": {
                "file_id": "voice123",
                "file_unique_id": "unique123",
                "duration": 5,
                "mime_type": "audio/ogg",
                "file_size": 1024,
            },
        }
    }

    result = await router_with_audio.process_update(update)

    # Should return accumulator feedback since feedback is enabled by default
    assert result is not None
    chat_id, response = result
    assert chat_id == 123
    assert "Message stored" in response and "1 message ready" in response

    # Verify audio processor was called
    mock_audio_processor.process_audio_message.assert_called_once_with(update)

    # Verify chat action was sent
    mock_audio_processor.telegram_client.send_chat_action.assert_called_once_with(123, "typing")

    # Verify logging
    mock_chat_logger.log_message.assert_called_once()
    call_args = mock_chat_logger.log_message.call_args[1]
    assert call_args["chat_id"] == 123
    assert call_args["message_type"] == "message"  # Logged as regular message after transcription
    assert call_args["text"] == "Hello world"


@pytest.mark.asyncio
async def test_process_audio_message_no_feedback_confirmation(
    router_with_audio_no_feedback, mock_audio_processor, mock_chat_logger
):
    """Test audio processing with no accumulator feedback returns confirmation message."""
    update = {
        "message": {
            "chat": {"id": 123},
            "from": {"id": 456, "username": "testuser"},
            "voice": {
                "file_id": "voice123",
                "file_unique_id": "unique123",
                "duration": 5,
                "mime_type": "audio/ogg",
                "file_size": 1024,
            },
        }
    }

    result = await router_with_audio_no_feedback.process_update(update)

    # Should return confirmation message when no accumulator feedback
    assert result is not None
    chat_id, response = result
    assert chat_id == 123
    assert response == 'I heard: "Hello world"'

    # Verify audio processor was called
    mock_audio_processor.process_audio_message.assert_called_once_with(update)

    # Verify logging - should be called twice (once for message, once for audio confirmation)
    assert mock_chat_logger.log_message.call_count == 2

    # Check the first call (regular message processing)
    first_call_args = mock_chat_logger.log_message.call_args_list[0][1]
    assert first_call_args["chat_id"] == 123
    assert first_call_args["message_type"] == "message"
    assert first_call_args["text"] == "Hello world"

    # Check the second call (audio confirmation)
    second_call_args = mock_chat_logger.log_message.call_args_list[1][1]
    assert second_call_args["chat_id"] == 123
    assert second_call_args["message_type"] == "audio"
    assert "[Audio transcribed]: Hello world" in second_call_args["text"]


@pytest.mark.asyncio
async def test_process_audio_message_audio_file_success(router_with_audio, mock_audio_processor):
    """Test successful processing of audio file."""
    update = {
        "message": {
            "chat": {"id": 123},
            "from": {"id": 456, "username": "testuser"},
            "audio": {
                "file_id": "audio123",
                "file_unique_id": "unique123",
                "duration": 10,
                "mime_type": "audio/mp3",
                "file_size": 2048,
            },
        }
    }

    result = await router_with_audio.process_update(update)

    # Should return accumulator feedback
    assert result is not None
    chat_id, response = result
    assert chat_id == 123
    assert "Message stored" in response

    # Verify audio processor was called
    mock_audio_processor.process_audio_message.assert_called_once_with(update)


@pytest.mark.asyncio
async def test_process_audio_message_video_note_success(router_with_audio, mock_audio_processor):
    """Test successful processing of video note."""
    update = {
        "message": {
            "chat": {"id": 123},
            "from": {"id": 456, "username": "testuser"},
            "video_note": {
                "file_id": "video123",
                "file_unique_id": "unique123",
                "duration": 3,
                "file_size": 512,
            },
        }
    }

    result = await router_with_audio.process_update(update)

    # Should return accumulator feedback
    assert result is not None
    chat_id, response = result
    assert chat_id == 123
    assert "Message stored" in response

    # Verify audio processor was called
    mock_audio_processor.process_audio_message.assert_called_once_with(update)


@pytest.mark.asyncio
async def test_process_audio_message_command_transcription(
    router_with_audio, mock_audio_processor, mock_mcp_service, mock_registry
):
    """Test processing audio message that transcribes to a command."""
    # Mock transcription to return a command
    mock_audio_processor.process_audio_message.return_value = "/echo_echo test command"

    update = {
        "message": {
            "chat": {"id": 123},
            "from": {"id": 456, "username": "testuser"},
            "voice": {
                "file_id": "voice123",
                "file_unique_id": "unique123",
                "duration": 5,
            },
        }
    }

    result = await router_with_audio.process_update(update)

    # Should process as command and return cattackle response
    assert result is not None
    chat_id, response = result
    assert chat_id == 123
    assert "test response" in str(response)

    # Verify MCP service was called for command execution
    mock_mcp_service.execute_cattackle.assert_called_once()


@pytest.mark.asyncio
async def test_process_audio_message_no_processor(router_no_audio, mock_chat_logger):
    """Test audio message when no audio processor is available."""
    update = {
        "message": {
            "chat": {"id": 123},
            "from": {"id": 456, "username": "testuser"},
            "voice": {
                "file_id": "voice123",
                "file_unique_id": "unique123",
                "duration": 5,
            },
        }
    }

    result = await router_no_audio.process_update(update)

    # Should return unavailable message
    assert result is not None
    chat_id, response = result
    assert chat_id == 123
    assert response == "Sorry, audio processing is not available at the moment."

    # Verify logging
    mock_chat_logger.log_message.assert_called_once()
    call_args = mock_chat_logger.log_message.call_args[1]
    assert call_args["message_type"] == "audio"
    assert "processing unavailable" in call_args["text"]


@pytest.mark.asyncio
async def test_process_audio_message_processing_error(router_with_audio, mock_audio_processor, mock_chat_logger):
    """Test handling of audio processing errors."""
    # Mock processor to raise an error
    mock_audio_processor.process_audio_message.side_effect = AudioProcessingError("File too large")

    update = {
        "message": {
            "chat": {"id": 123},
            "from": {"id": 456, "username": "testuser"},
            "voice": {
                "file_id": "voice123",
                "file_unique_id": "unique123",
                "duration": 5,
            },
        }
    }

    result = await router_with_audio.process_update(update)

    # Should return user-friendly error message
    assert result is not None
    chat_id, response = result
    assert chat_id == 123
    assert "too large" in response

    # Verify error logging
    mock_chat_logger.log_message.assert_called_once()
    call_args = mock_chat_logger.log_message.call_args[1]
    assert call_args["message_type"] == "audio"
    assert "Audio processing error" in call_args["text"]


@pytest.mark.asyncio
async def test_process_audio_message_different_error_types(router_with_audio, mock_audio_processor):
    """Test different types of audio processing errors return appropriate messages."""
    test_cases = [
        ("File too long", "too long"),
        ("Unsupported format", "can't process this audio format"),
        ("Audio processing is disabled", "currently disabled"),
        ("API key not configured", "not properly configured"),
        ("Unknown error", "try again later"),
    ]

    for error_message, expected_response_part in test_cases:
        mock_audio_processor.process_audio_message.side_effect = AudioProcessingError(error_message)

        update = {
            "message": {
                "chat": {"id": 123},
                "from": {"id": 456, "username": "testuser"},
                "voice": {"file_id": "voice123", "file_unique_id": "unique123", "duration": 5},
            }
        }

        result = await router_with_audio.process_update(update)

        assert result is not None
        chat_id, response = result
        assert chat_id == 123
        assert expected_response_part in response.lower()


@pytest.mark.asyncio
async def test_process_audio_message_unexpected_error(router_with_audio, mock_audio_processor, mock_chat_logger):
    """Test handling of unexpected errors during audio processing."""
    # Mock processor to raise an unexpected error
    mock_audio_processor.process_audio_message.side_effect = Exception("Unexpected error")

    update = {
        "message": {
            "chat": {"id": 123},
            "from": {"id": 456, "username": "testuser"},
            "voice": {
                "file_id": "voice123",
                "file_unique_id": "unique123",
                "duration": 5,
            },
        }
    }

    result = await router_with_audio.process_update(update)

    # Should return generic error message
    assert result is not None
    chat_id, response = result
    assert chat_id == 123
    assert "unexpected error occurred" in response

    # Verify error logging
    mock_chat_logger.log_message.assert_called_once()
    call_args = mock_chat_logger.log_message.call_args[1]
    assert call_args["message_type"] == "audio"
    assert "unexpected error" in call_args["text"]


@pytest.mark.asyncio
async def test_process_audio_message_empty_transcription(router_with_audio, mock_audio_processor, mock_chat_logger):
    """Test handling when audio processing returns empty transcription."""
    # Mock processor to return None/empty
    mock_audio_processor.process_audio_message.return_value = None

    update = {
        "message": {
            "chat": {"id": 123},
            "from": {"id": 456, "username": "testuser"},
            "voice": {
                "file_id": "voice123",
                "file_unique_id": "unique123",
                "duration": 5,
            },
        }
    }

    result = await router_with_audio.process_update(update)

    # Should return failure message
    assert result is not None
    chat_id, response = result
    assert chat_id == 123
    assert "couldn't process the audio message" in response

    # Verify logging
    mock_chat_logger.log_message.assert_called_once()
    call_args = mock_chat_logger.log_message.call_args[1]
    assert call_args["message_type"] == "audio"
    assert "processing failed" in call_args["text"]


@pytest.mark.asyncio
async def test_audio_message_detection_priority(router_with_audio, mock_audio_processor):
    """Test that audio messages are detected even when text is also present."""
    update = {
        "message": {
            "chat": {"id": 123},
            "from": {"id": 456, "username": "testuser"},
            "text": "This should be ignored",  # Text present but should be ignored
            "voice": {
                "file_id": "voice123",
                "file_unique_id": "unique123",
                "duration": 5,
            },
        }
    }

    result = await router_with_audio.process_update(update)

    # Should process as audio, not text
    assert result is not None
    chat_id, response = result
    assert chat_id == 123
    assert "Message stored" in response  # Accumulator feedback

    # Verify audio processor was called
    mock_audio_processor.process_audio_message.assert_called_once_with(update)
