"""Tests for Telegram client."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from catmandu.core.clients.telegram import TelegramClient


@pytest.fixture
def telegram_client():
    """Create a Telegram client instance."""
    return TelegramClient(token="test-token")


@pytest.mark.asyncio
async def test_get_updates_success(telegram_client):
    """Test successful get_updates call."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "ok": True,
        "result": [
            {"update_id": 1, "message": {"text": "hello"}},
            {"update_id": 2, "message": {"text": "world"}},
        ],
    }

    with patch.object(telegram_client._client, "get", return_value=mock_response) as mock_get:
        updates = await telegram_client.get_updates(offset=123, timeout=30)

        assert len(updates) == 2
        assert updates[0]["update_id"] == 1
        assert updates[1]["update_id"] == 2
        mock_get.assert_called_once_with("/getUpdates", params={"timeout": 30, "offset": 123})


@pytest.mark.asyncio
async def test_get_updates_api_error(telegram_client):
    """Test get_updates with API error response."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"ok": False, "error_code": 400, "description": "Bad Request"}

    with patch.object(telegram_client._client, "get", return_value=mock_response):
        updates = await telegram_client.get_updates()

        assert updates == []


@pytest.mark.asyncio
async def test_get_updates_http_error(telegram_client):
    """Test get_updates with HTTP error."""
    with patch.object(telegram_client._client, "get", side_effect=httpx.HTTPError("Network error")):
        updates = await telegram_client.get_updates()

        assert updates == []


@pytest.mark.asyncio
async def test_send_message_success(telegram_client):
    """Test successful send_message call."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"ok": True, "result": {"message_id": 123, "text": "Hello, World!"}}

    with patch.object(telegram_client._client, "post", return_value=mock_response) as mock_post:
        result = await telegram_client.send_message(chat_id=456, text="Hello, World!")

        assert result["message_id"] == 123
        assert result["text"] == "Hello, World!"
        mock_post.assert_called_once_with("/sendMessage", json={"chat_id": 456, "text": "Hello, World!"})


@pytest.mark.asyncio
async def test_send_message_api_error(telegram_client):
    """Test send_message with API error response."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"ok": False, "error_code": 400, "description": "Bad Request"}

    with patch.object(telegram_client._client, "post", return_value=mock_response):
        result = await telegram_client.send_message(chat_id=456, text="Hello, World!")

        assert result is None


@pytest.mark.asyncio
async def test_send_message_http_error(telegram_client):
    """Test send_message with HTTP error."""
    with patch.object(telegram_client._client, "post", side_effect=httpx.HTTPError("Network error")):
        result = await telegram_client.send_message(chat_id=456, text="Hello, World!")

        assert result is None


@pytest.mark.asyncio
async def test_close(telegram_client):
    """Test client cleanup."""
    # Create a mock for the is_closed property
    mock_is_closed = MagicMock(return_value=False)
    # Use patch.object with property() to mock the property
    with patch.object(type(telegram_client._client), "is_closed", property(mock_is_closed)):
        with patch.object(telegram_client._client, "aclose") as mock_close:
            await telegram_client.close()
            mock_close.assert_called_once()


@pytest.mark.asyncio
async def test_close_already_closed(telegram_client):
    """Test client cleanup when already closed."""
    # Create a mock for the is_closed property
    mock_is_closed = MagicMock(return_value=True)
    # Use patch.object with property() to mock the property
    with patch.object(type(telegram_client._client), "is_closed", property(mock_is_closed)):
        with patch.object(telegram_client._client, "aclose") as mock_close:
            await telegram_client.close()
            mock_close.assert_not_called()


@pytest.mark.asyncio
async def test_get_file_success(telegram_client):
    """Test successful get_file call."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "ok": True,
        "result": {
            "file_id": "test_file_123",
            "file_unique_id": "unique_123",
            "file_size": 50000,
            "file_path": "voice/file_123.ogg",
        },
    }

    with patch.object(telegram_client._client, "post", return_value=mock_response) as mock_post:
        result = await telegram_client.get_file("test_file_123")

        assert result["file_id"] == "test_file_123"
        assert result["file_path"] == "voice/file_123.ogg"
        mock_post.assert_called_once_with("/getFile", json={"file_id": "test_file_123"})


@pytest.mark.asyncio
async def test_get_file_api_error(telegram_client):
    """Test get_file with API error response."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"ok": False, "error_code": 400, "description": "File not found"}

    with patch.object(telegram_client._client, "post", return_value=mock_response):
        result = await telegram_client.get_file("test_file_123")

        assert result is None


@pytest.mark.asyncio
async def test_get_file_http_error(telegram_client):
    """Test get_file with HTTP error."""
    with patch.object(telegram_client._client, "post", side_effect=httpx.HTTPError("Network error")):
        result = await telegram_client.get_file("test_file_123")

        assert result is None


@pytest.mark.asyncio
async def test_download_file_success(telegram_client):
    """Test successful file download."""
    mock_response = MagicMock()
    mock_response.content = b"fake_audio_data"

    with patch.object(telegram_client._client, "get", return_value=mock_response) as mock_get:
        result = await telegram_client.download_file("voice/file_123.ogg")

        assert result == b"fake_audio_data"
        # Check that the correct download URL was used
        expected_url = f"https://api.telegram.org/file/bot{telegram_client._api_url.split('bot')[1]}/voice/file_123.ogg"
        mock_get.assert_called_once_with(expected_url)


@pytest.mark.asyncio
async def test_download_file_http_error(telegram_client):
    """Test file download with HTTP error."""
    with patch.object(telegram_client._client, "get", side_effect=httpx.HTTPError("Network error")):
        result = await telegram_client.download_file("voice/file_123.ogg")

        assert result is None


@pytest.mark.asyncio
async def test_send_chat_action_success(telegram_client):
    """Test successful send_chat_action call."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"ok": True, "result": True}

    with patch.object(telegram_client._client, "post", return_value=mock_response) as mock_post:
        result = await telegram_client.send_chat_action(chat_id=456, action="typing")

        assert result is True
        mock_post.assert_called_once_with("/sendChatAction", json={"chat_id": 456, "action": "typing"})


@pytest.mark.asyncio
async def test_send_chat_action_api_error(telegram_client):
    """Test send_chat_action with API error response."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"ok": False, "error_code": 400, "description": "Bad Request"}

    with patch.object(telegram_client._client, "post", return_value=mock_response):
        result = await telegram_client.send_chat_action(chat_id=456, action="typing")

        assert result is False


@pytest.mark.asyncio
async def test_send_chat_action_http_error(telegram_client):
    """Test send_chat_action with HTTP error."""
    with patch.object(telegram_client._client, "post", side_effect=httpx.HTTPError("Network error")):
        result = await telegram_client.send_chat_action(chat_id=456, action="typing")

        assert result is False
