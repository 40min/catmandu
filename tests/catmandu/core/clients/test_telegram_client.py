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
