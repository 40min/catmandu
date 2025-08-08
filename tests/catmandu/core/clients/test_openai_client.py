from unittest.mock import AsyncMock, patch

import aiohttp
import pytest

from catmandu.core.clients.openai_client import OpenAIClient


class TestOpenAIClient:
    """Test cases for OpenAI client."""

    @pytest.fixture
    def client(self):
        """Create OpenAI client for testing."""
        return OpenAIClient(api_key="sk-test-key", model_name="gpt-5-nano", timeout=30)

    @pytest.fixture
    def mock_session(self):
        """Create mock aiohttp session."""
        session = AsyncMock(spec=aiohttp.ClientSession)
        session.closed = False
        return session

    def test_init(self):
        """Test client initialization."""
        client = OpenAIClient(api_key="sk-test-key", model_name="gpt-5-nano", timeout=60)
        assert client.api_key == "sk-test-key"
        assert client.model_name == "gpt-5-nano"
        assert client.timeout == 60
        assert client.base_url == "https://api.openai.com/v1"
        assert client._session is None

    @pytest.mark.asyncio
    async def test_get_session_creates_new_session(self, client):
        """Test that _get_session creates a new session with proper headers."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session.closed = False
            mock_session_class.return_value = mock_session

            session = await client._get_session()

            assert session == mock_session
            mock_session_class.assert_called_once()

            # Verify headers were set correctly
            call_args = mock_session_class.call_args
            headers = call_args.kwargs["headers"]
            assert headers["Authorization"] == "Bearer sk-test-key"
            assert headers["User-Agent"] == "Catmandu-Bot/1.0"

    @pytest.mark.asyncio
    async def test_transcribe_audio_success(self, client, mock_session):
        """Test successful audio transcription."""
        # Mock response data
        response_data = {"text": "Hello world", "language": "en", "duration": 2.5}

        # Mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = response_data
        mock_session.post.return_value.__aenter__.return_value = mock_response

        # Mock _get_session to return our mock session
        client._get_session = AsyncMock(return_value=mock_session)

        # Test transcription
        audio_data = b"fake audio data"
        result = await client.transcribe_audio(audio_data, "test.mp3")

        assert result == response_data
        mock_session.post.assert_called_once()

        # Verify URL
        call_args = mock_session.post.call_args
        assert call_args[0][0] == "https://api.openai.com/v1/audio/transcriptions"

    @pytest.mark.asyncio
    async def test_transcribe_audio_api_error(self, client, mock_session):
        """Test transcription with API error."""
        # Mock error response
        error_response = {"error": {"message": "Invalid audio format"}}

        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.json.return_value = error_response
        mock_session.post.return_value.__aenter__.return_value = mock_response

        client._get_session = AsyncMock(return_value=mock_session)

        # Test that error is raised
        with pytest.raises(ValueError, match="Whisper API error: Invalid audio format"):
            await client.transcribe_audio(b"fake audio", "test.mp3")

    @pytest.mark.asyncio
    async def test_improve_text_success(self, client, mock_session):
        """Test successful text improvement."""
        # Mock response data
        response_data = {
            "choices": [{"message": {"content": "Hello, world! This is improved text."}}],
            "usage": {"prompt_tokens": 50, "completion_tokens": 20, "total_tokens": 70},
        }

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = response_data
        mock_session.post.return_value.__aenter__.return_value = mock_response

        client._get_session = AsyncMock(return_value=mock_session)

        # Test text improvement
        result = await client.improve_text("hello world this is text")

        assert result["text"] == "Hello, world! This is improved text."
        assert result["usage"]["prompt_tokens"] == 50
        assert result["usage"]["completion_tokens"] == 20
        assert result["model"] == "gpt-5-nano"

        mock_session.post.assert_called_once()

        # Verify URL and payload
        call_args = mock_session.post.call_args
        assert call_args[0][0] == "https://api.openai.com/v1/chat/completions"
        payload = call_args.kwargs["json"]
        assert payload["model"] == "gpt-5-nano"
        assert payload["messages"][1]["content"] == "hello world this is text"

    @pytest.mark.asyncio
    async def test_improve_text_empty_text(self, client):
        """Test text improvement with empty text."""
        with pytest.raises(ValueError, match="Text cannot be empty"):
            await client.improve_text("")

    @pytest.mark.asyncio
    async def test_improve_text_custom_prompt(self, client, mock_session):
        """Test text improvement with custom prompt."""
        response_data = {
            "choices": [{"message": {"content": "Improved text"}}],
            "usage": {"prompt_tokens": 30, "completion_tokens": 10},
        }

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = response_data
        mock_session.post.return_value.__aenter__.return_value = mock_response

        client._get_session = AsyncMock(return_value=mock_session)

        custom_prompt = "Make this text more formal"
        await client.improve_text("hello", custom_prompt)

        # Verify custom prompt was used
        call_args = mock_session.post.call_args
        payload = call_args.kwargs["json"]
        assert payload["messages"][0]["content"] == custom_prompt

    @pytest.mark.asyncio
    async def test_improve_text_api_error(self, client, mock_session):
        """Test text improvement with API error."""
        error_response = {"error": {"message": "Rate limit exceeded"}}

        mock_response = AsyncMock()
        mock_response.status = 429
        mock_response.json.return_value = error_response
        mock_session.post.return_value.__aenter__.return_value = mock_response

        client._get_session = AsyncMock(return_value=mock_session)

        with pytest.raises(ValueError, match="OpenAI API error: Rate limit exceeded"):
            await client.improve_text("test text")

    @pytest.mark.asyncio
    async def test_close(self, client):
        """Test client close method."""
        mock_session = AsyncMock()
        mock_session.closed = False
        client._session = mock_session

        await client.close()

        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_no_session(self, client):
        """Test close when no session exists."""
        # Should not raise any errors
        await client.close()

    @pytest.mark.asyncio
    async def test_context_manager(self, client):
        """Test async context manager functionality."""
        async with client as ctx_client:
            assert ctx_client == client

        # Close should have been called (but we don't have a session to verify)
        # This test mainly ensures the context manager methods exist and work
