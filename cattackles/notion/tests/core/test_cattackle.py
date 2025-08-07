"""Tests for the NotionCattackle core business logic."""

import unittest.mock
from unittest.mock import AsyncMock, patch

import pytest
from notion.clients.notion_client import NotionClientWrapper
from notion.core.cattackle import NotionCattackle
from notion_client.errors import APIResponseError, RequestTimeoutError


class TestNotionCattackle:
    """Test suite for NotionCattackle core business logic."""

    @pytest.fixture
    def cattackle(self):
        """Create a NotionCattackle instance for testing."""
        return NotionCattackle()

    @pytest.fixture
    def mock_notion_client(self):
        """Create a mock NotionClientWrapper for testing."""
        mock_client = AsyncMock(spec=NotionClientWrapper)
        return mock_client

    @pytest.fixture
    def sample_user_config(self):
        """Sample user configuration for testing."""
        return {"token": "secret_test_token", "parent_page_id": "test_parent_page_id"}

    @pytest.mark.asyncio
    async def test_save_to_notion_success_new_page(self, cattackle, mock_notion_client, sample_user_config):
        """Test successful message saving with new page creation."""
        username = "testuser"
        message_content = "Test message content"
        expected_page_id = "new_page_id_123"
        expected_date = "2025-08-05"

        # Mock user configuration
        with (
            patch("notion.core.cattackle.is_user_authorized", return_value=True),
            patch("notion.core.cattackle.get_user_config", return_value=sample_user_config),
            patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client),
            patch("notion.core.cattackle.format_date_for_page_title", return_value=expected_date),
        ):

            # Mock page doesn't exist, so create new one
            mock_notion_client.find_page_by_title.return_value = None
            mock_notion_client.create_page.return_value = expected_page_id
            mock_notion_client.append_content_to_page.return_value = None

            result = await cattackle.save_to_notion(username, message_content)

            # Verify the result
            assert result == f"✅ Message saved to Notion page for {expected_date}"

            # Verify method calls use date format for page operations
            mock_notion_client.find_page_by_title.assert_called_once_with(
                sample_user_config["parent_page_id"], expected_date
            )
            mock_notion_client.create_page.assert_called_once_with(sample_user_config["parent_page_id"], expected_date)
            mock_notion_client.append_content_to_page.assert_called_once()

            # Verify the content includes timestamp
            call_args = mock_notion_client.append_content_to_page.call_args
            assert call_args[0][0] == expected_page_id  # page_id
            assert message_content in call_args[0][1]  # content includes original message
            assert "[" in call_args[0][1] and "]" in call_args[0][1]  # timestamp format

    @pytest.mark.asyncio
    async def test_save_to_notion_success_existing_page(self, cattackle, mock_notion_client, sample_user_config):
        """Test successful message saving with existing page."""
        username = "testuser"
        message_content = "Test message content"
        existing_page_id = "existing_page_id_456"
        expected_date = "2025-08-05"

        # Mock user configuration
        with (
            patch("notion.core.cattackle.is_user_authorized", return_value=True),
            patch("notion.core.cattackle.get_user_config", return_value=sample_user_config),
            patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client),
            patch("notion.core.cattackle.format_date_for_page_title", return_value=expected_date),
        ):

            # Mock page exists
            mock_notion_client.find_page_by_title.return_value = existing_page_id
            mock_notion_client.append_content_to_page.return_value = None

            result = await cattackle.save_to_notion(username, message_content)

            # Verify the result
            assert result == f"✅ Message saved to Notion page for {expected_date}"

            # Verify method calls use date format
            mock_notion_client.find_page_by_title.assert_called_once_with(
                sample_user_config["parent_page_id"], expected_date
            )
            mock_notion_client.create_page.assert_not_called()  # Should not create new page
            mock_notion_client.append_content_to_page.assert_called_once_with(existing_page_id, unittest.mock.ANY)

    @pytest.mark.asyncio
    async def test_save_to_notion_with_accumulated_params(self, cattackle, mock_notion_client, sample_user_config):
        """Test message saving with accumulated parameters."""
        username = "testuser"
        message_content = "final message"
        accumulated_params = ["accumulated", "text", "here"]
        existing_page_id = "existing_page_id_789"

        # Mock user configuration
        with (
            patch("notion.core.cattackle.is_user_authorized", return_value=True),
            patch("notion.core.cattackle.get_user_config", return_value=sample_user_config),
            patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client),
            patch("notion.core.cattackle.format_date_for_page_title", return_value="2025-08-05"),
        ):

            # Mock page exists
            mock_notion_client.find_page_by_title.return_value = existing_page_id
            mock_notion_client.append_content_to_page.return_value = None

            result = await cattackle.save_to_notion(username, message_content, accumulated_params)

            # Verify the result
            assert result == "✅ Message saved to Notion page for 2025-08-05"

            # Verify the content includes both accumulated params and message
            call_args = mock_notion_client.append_content_to_page.call_args
            content = call_args[0][1]
            assert "accumulated text here final message" in content

    @pytest.mark.asyncio
    async def test_save_to_notion_unauthorized_user_silent_skip(self, cattackle):
        """Test that unauthorized users are silently skipped."""
        username = "unauthorized_user"
        message_content = "Test message"

        with patch("notion.core.cattackle.is_user_authorized", return_value=False):
            result = await cattackle.save_to_notion(username, message_content)

            # Should return message for unauthorized user
            assert result == "User not configured for Notion integration"

    @pytest.mark.asyncio
    async def test_save_to_notion_config_error(self, cattackle):
        """Test handling of configuration errors."""
        username = "testuser"
        message_content = "Test message"

        with (
            patch("notion.core.cattackle.is_user_authorized", return_value=True),
            patch("notion.core.cattackle.get_user_config", return_value=None),
        ):

            result = await cattackle.save_to_notion(username, message_content)

            assert result == "❌ Configuration error. Please contact administrator."

    @pytest.mark.asyncio
    async def test_save_to_notion_notion_api_error(self, cattackle, mock_notion_client, sample_user_config):
        """Test handling of generic API errors (now masked for security)."""
        username = "testuser"
        message_content = "Test message"

        # Mock user configuration
        with (
            patch("notion.core.cattackle.is_user_authorized", return_value=True),
            patch("notion.core.cattackle.get_user_config", return_value=sample_user_config),
            patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client),
        ):

            # Mock generic API error (not a specific APIResponseError)
            mock_notion_client.find_page_by_title.side_effect = Exception("API Error")

            result = await cattackle.save_to_notion(username, message_content)

            # Should return generic error message for security
            assert result == "❌ An unexpected error occurred. Please try again later."

    @pytest.mark.asyncio
    async def test_get_or_create_daily_page_existing_page(self, cattackle, mock_notion_client):
        """Test getting an existing daily page."""
        parent_page_id = "parent_page_id"
        date = "2024-01-15"
        existing_page_id = "existing_page_123"

        mock_notion_client.find_page_by_title.return_value = existing_page_id

        result = await cattackle._get_or_create_daily_page(mock_notion_client, parent_page_id, date)

        assert result == existing_page_id
        mock_notion_client.find_page_by_title.assert_called_once_with(parent_page_id, date)
        mock_notion_client.create_page.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_daily_page_new_page(self, cattackle, mock_notion_client):
        """Test creating a new daily page."""
        parent_page_id = "parent_page_id"
        date = "2024-01-15"
        new_page_id = "new_page_456"

        mock_notion_client.find_page_by_title.return_value = None
        mock_notion_client.create_page.return_value = new_page_id

        result = await cattackle._get_or_create_daily_page(mock_notion_client, parent_page_id, date)

        assert result == new_page_id
        mock_notion_client.find_page_by_title.assert_called_once_with(parent_page_id, date)
        mock_notion_client.create_page.assert_called_once_with(parent_page_id, date)

    @pytest.mark.asyncio
    async def test_get_or_create_daily_page_error(self, cattackle, mock_notion_client):
        """Test error handling in page creation."""
        parent_page_id = "parent_page_id"
        date = "2024-01-15"

        mock_notion_client.find_page_by_title.side_effect = Exception("Search failed")

        with pytest.raises(Exception, match="❌ An unexpected error occurred. Please try again later."):
            await cattackle._get_or_create_daily_page(mock_notion_client, parent_page_id, date)

    @pytest.mark.asyncio
    async def test_append_message_to_page_success(self, cattackle, mock_notion_client):
        """Test successful message appending."""
        page_id = "test_page_id"
        content = "Test message content"

        mock_notion_client.append_content_to_page.return_value = None

        await cattackle._append_message_to_page(mock_notion_client, page_id, content)

        mock_notion_client.append_content_to_page.assert_called_once()
        call_args = mock_notion_client.append_content_to_page.call_args
        assert call_args[0][0] == page_id
        # Verify timestamp format is added
        formatted_content = call_args[0][1]
        assert content in formatted_content
        assert "[" in formatted_content and "]" in formatted_content

    @pytest.mark.asyncio
    async def test_append_message_to_page_error(self, cattackle, mock_notion_client):
        """Test error handling in message appending."""
        page_id = "test_page_id"
        content = "Test message content"

        mock_notion_client.append_content_to_page.side_effect = Exception("Append failed")

        with pytest.raises(Exception, match="❌ An unexpected error occurred. Please try again later."):
            await cattackle._append_message_to_page(mock_notion_client, page_id, content)

    @pytest.mark.asyncio
    async def test_date_formatting(self, cattackle, mock_notion_client, sample_user_config):
        """Test that date formatting is consistent (YYYY-MM-DD)."""
        username = "testuser"
        message_content = "Test message"

        with (
            patch("notion.core.cattackle.is_user_authorized", return_value=True),
            patch("notion.core.cattackle.get_user_config", return_value=sample_user_config),
            patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client),
        ):

            mock_notion_client.find_page_by_title.return_value = "existing_page"
            mock_notion_client.append_content_to_page.return_value = None

            # Mock date formatting function to ensure consistent testing
            with patch("notion.core.cattackle.format_date_for_page_title", return_value="2024-01-15"):

                await cattackle.save_to_notion(username, message_content)

                # Verify date format used in page lookup
                mock_notion_client.find_page_by_title.assert_called_once_with(
                    sample_user_config["parent_page_id"], "2024-01-15"
                )

    @pytest.mark.asyncio
    async def test_empty_message_content(self, cattackle, mock_notion_client, sample_user_config):
        """Test handling of empty message content."""
        username = "testuser"
        message_content = ""

        with (
            patch("notion.core.cattackle.is_user_authorized", return_value=True),
            patch("notion.core.cattackle.get_user_config", return_value=sample_user_config),
            patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client),
            patch("notion.core.cattackle.format_date_for_page_title", return_value="2025-08-05"),
        ):

            mock_notion_client.find_page_by_title.return_value = "existing_page"
            mock_notion_client.append_content_to_page.return_value = None

            result = await cattackle.save_to_notion(username, message_content)

            # Should still process empty content
            assert result == "✅ Message saved to Notion page for 2025-08-05"
            mock_notion_client.append_content_to_page.assert_called_once()

    @pytest.mark.asyncio
    async def test_api_response_error_401_unauthorized(self, cattackle, mock_notion_client, sample_user_config):
        """Test handling of 401 Unauthorized API error."""
        username = "testuser"
        message_content = "Test message"

        with (
            patch("notion.core.cattackle.is_user_authorized", return_value=True),
            patch("notion.core.cattackle.get_user_config", return_value=sample_user_config),
            patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client),
        ):

            # Mock 401 API error
            api_error = APIResponseError(
                response=unittest.mock.MagicMock(status_code=401), message="Unauthorized", code="unauthorized"
            )
            api_error.status = 401
            api_error.code = "unauthorized"
            mock_notion_client.find_page_by_title.side_effect = api_error

            result = await cattackle.save_to_notion(username, message_content)

            assert result == "❌ Authentication failed. Please check your Notion integration token."

    @pytest.mark.asyncio
    async def test_api_response_error_404_object_not_found(self, cattackle, mock_notion_client, sample_user_config):
        """Test handling of 404 object not found API error."""
        username = "testuser"
        message_content = "Test message"

        with (
            patch("notion.core.cattackle.is_user_authorized", return_value=True),
            patch("notion.core.cattackle.get_user_config", return_value=sample_user_config),
            patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client),
        ):

            # Mock 404 API error with object_not_found code
            api_error = APIResponseError(
                response=unittest.mock.MagicMock(status_code=404), message="Object not found", code="object_not_found"
            )
            api_error.status = 404
            api_error.code = "object_not_found"
            mock_notion_client.find_page_by_title.side_effect = api_error

            result = await cattackle.save_to_notion(username, message_content)

            assert result == "❌ The configured parent page was not found. Please check your configuration."

    @pytest.mark.asyncio
    async def test_api_response_error_429_rate_limit(self, cattackle, mock_notion_client, sample_user_config):
        """Test handling of 429 rate limit API error."""
        username = "testuser"
        message_content = "Test message"

        with (
            patch("notion.core.cattackle.is_user_authorized", return_value=True),
            patch("notion.core.cattackle.get_user_config", return_value=sample_user_config),
            patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client),
        ):

            # Mock 429 API error
            api_error = APIResponseError(
                response=unittest.mock.MagicMock(status_code=429), message="Rate limited", code="rate_limited"
            )
            api_error.status = 429
            api_error.code = "rate_limited"
            mock_notion_client.find_page_by_title.side_effect = api_error

            result = await cattackle.save_to_notion(username, message_content)

            assert result == "❌ Rate limit exceeded. Please try again in a few minutes."

    @pytest.mark.asyncio
    async def test_api_response_error_500_server_error(self, cattackle, mock_notion_client, sample_user_config):
        """Test handling of 500 server error."""
        username = "testuser"
        message_content = "Test message"

        with (
            patch("notion.core.cattackle.is_user_authorized", return_value=True),
            patch("notion.core.cattackle.get_user_config", return_value=sample_user_config),
            patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client),
        ):

            # Mock 500 API error
            api_error = APIResponseError(
                response=unittest.mock.MagicMock(status_code=500),
                message="Internal server error",
                code="internal_server_error",
            )
            api_error.status = 500
            api_error.code = "internal_server_error"
            mock_notion_client.find_page_by_title.side_effect = api_error

            result = await cattackle.save_to_notion(username, message_content)

            assert result == "❌ Notion service is temporarily unavailable. Please try again later."

    @pytest.mark.asyncio
    async def test_request_timeout_error(self, cattackle, mock_notion_client, sample_user_config):
        """Test handling of request timeout error."""
        username = "testuser"
        message_content = "Test message"

        with (
            patch("notion.core.cattackle.is_user_authorized", return_value=True),
            patch("notion.core.cattackle.get_user_config", return_value=sample_user_config),
            patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client),
        ):

            # Mock timeout error
            timeout_error = RequestTimeoutError("Request timed out")
            mock_notion_client.find_page_by_title.side_effect = timeout_error

            result = await cattackle.save_to_notion(username, message_content)

            assert result == "❌ Request timed out. Please try again later."

    @pytest.mark.asyncio
    async def test_value_error_handling(self, cattackle, mock_notion_client, sample_user_config):
        """Test handling of ValueError (now treated as unexpected error)."""
        username = "testuser"
        message_content = "Test message"

        with (
            patch("notion.core.cattackle.is_user_authorized", return_value=True),
            patch("notion.core.cattackle.get_user_config", return_value=sample_user_config),
            patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client),
        ):

            # Mock ValueError
            value_error = ValueError("Invalid configuration format")
            mock_notion_client.find_page_by_title.side_effect = value_error

            result = await cattackle.save_to_notion(username, message_content)

            # ValueError is now handled as unexpected error in helper methods
            assert result == "❌ An unexpected error occurred. Please try again later."

    @pytest.mark.asyncio
    async def test_unexpected_error_handling(self, cattackle, mock_notion_client, sample_user_config):
        """Test handling of unexpected errors."""
        username = "testuser"
        message_content = "Test message"

        with (
            patch("notion.core.cattackle.is_user_authorized", return_value=True),
            patch("notion.core.cattackle.get_user_config", return_value=sample_user_config),
            patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client),
        ):

            # Mock unexpected error
            unexpected_error = RuntimeError("Unexpected runtime error")
            mock_notion_client.find_page_by_title.side_effect = unexpected_error

            result = await cattackle.save_to_notion(username, message_content)

            assert result == "❌ An unexpected error occurred. Please try again later."

    def test_handle_api_error_method(self, cattackle):
        """Test the _handle_api_error method directly."""
        # Test 401 error
        error_401 = APIResponseError(
            response=unittest.mock.MagicMock(status_code=401), message="Unauthorized", code="unauthorized"
        )
        error_401.status = 401
        error_401.code = "unauthorized"
        result = cattackle._handle_api_error(error_401)
        assert result == "❌ Authentication failed. Please check your Notion integration token."

        # Test 403 error
        error_403 = APIResponseError(
            response=unittest.mock.MagicMock(status_code=403), message="Forbidden", code="forbidden"
        )
        error_403.status = 403
        error_403.code = "forbidden"
        result = cattackle._handle_api_error(error_403)
        assert result == "❌ Access denied. Please check your Notion integration permissions."

        # Test unknown error
        error_unknown = APIResponseError(
            response=unittest.mock.MagicMock(status_code=999), message="Unknown", code="unknown"
        )
        error_unknown.status = 999
        error_unknown.code = "unknown"
        result = cattackle._handle_api_error(error_unknown)
        assert result == "❌ Notion API error occurred. Please try again later."
