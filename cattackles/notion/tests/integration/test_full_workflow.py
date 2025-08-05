"""Integration tests for the complete Notion cattackle workflow.

These tests cover the full end-to-end workflow from MCP command handling
through to Notion API interactions, including user configuration validation,
page management, and content operations.
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from notion.clients.notion_client import NotionClientWrapper
from notion.core.cattackle import NotionCattackle
from notion.handlers.mcp_handlers import handle_tool_call
from notion_client.errors import RequestTimeoutError

from .test_utilities import MCPTestHelper, NotionAPIResponseBuilder


class TestFullWorkflowIntegration:
    """Integration tests for the complete workflow from MCP to Notion API."""

    @pytest.fixture
    def mock_notion_client(self):
        """Create a mock Notion client with standard responses."""
        client = MagicMock(spec=NotionClientWrapper)
        client.find_page_by_title = AsyncMock()
        client.create_page = AsyncMock()
        client.append_content_to_page = AsyncMock()
        return client

    @pytest.fixture
    def test_user_config(self):
        """Test user configuration."""
        return {"testuser": {"token": "secret_test_token_123", "parent_page_id": "test_parent_page_id_456"}}

    @pytest.fixture
    def cattackle(self):
        """Create a NotionCattackle instance for testing."""
        return NotionCattackle()

    @pytest.mark.asyncio
    async def test_complete_workflow_new_page_creation(self, cattackle, mock_notion_client, test_user_config):
        """Test the complete workflow when a new daily page needs to be created."""
        # Arrange
        today = datetime.now().strftime("%Y-%m-%d")
        test_message = "This is a test message for integration testing"

        # Mock user configuration
        with patch("notion.config.user_config.USER_CONFIGS", test_user_config):
            # Mock Notion client creation and responses
            with patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client):
                with (
                    patch("notion.core.cattackle.format_date_for_page_title", return_value="2025-08-05 10:30:45"),
                    patch("notion.core.cattackle.get_current_date_iso", return_value=today),
                ):
                    # Page doesn't exist yet
                    mock_notion_client.find_page_by_title.return_value = None
                    # Page creation returns new page ID
                    mock_notion_client.create_page.return_value = "new_page_id_789"
                    # Content appending succeeds
                    mock_notion_client.append_content_to_page.return_value = None

                    # Act - Call through MCP handler to test full integration
                    arguments = {"text": test_message, "username": "testuser"}
                    result = await handle_tool_call(cattackle, "to_notion", arguments)

                    # Assert - Response format
                    assert len(result) == 1
                    response_data = json.loads(result[0].text)
                    assert response_data["data"] == f"✅ Message saved to Notion page for {today}"
                    assert response_data["error"] == ""

                    # Assert - Notion client interactions use full datetime
                    mock_notion_client.find_page_by_title.assert_called_once_with(
                        "test_parent_page_id_456", "2025-08-05 10:30:45"
                    )
                    mock_notion_client.create_page.assert_called_once_with(
                        "test_parent_page_id_456", "2025-08-05 10:30:45"
                    )

                # Verify content was appended with timestamp
                mock_notion_client.append_content_to_page.assert_called_once()
                call_args = mock_notion_client.append_content_to_page.call_args
                assert call_args[0][0] == "new_page_id_789"  # page_id
                appended_content = call_args[0][1]  # content
                assert test_message in appended_content
                assert "[" in appended_content and "]" in appended_content  # timestamp format

    @pytest.mark.asyncio
    async def test_complete_workflow_existing_page(self, cattackle, mock_notion_client, test_user_config):
        """Test the complete workflow when daily page already exists."""
        # Arrange
        today = datetime.now().strftime("%Y-%m-%d")
        test_message = "Another test message"

        with patch("notion.config.user_config.USER_CONFIGS", test_user_config):
            with patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client):
                with (
                    patch("notion.core.cattackle.format_date_for_page_title", return_value="2025-08-05 10:30:45"),
                    patch("notion.core.cattackle.get_current_date_iso", return_value=today),
                ):
                    # Page already exists
                    mock_notion_client.find_page_by_title.return_value = "existing_page_id_123"
                    # Content appending succeeds
                    mock_notion_client.append_content_to_page.return_value = None

                    # Act
                    arguments = {"text": test_message, "username": "testuser"}
                    result = await handle_tool_call(cattackle, "to_notion", arguments)

                    # Assert - Response format
                    assert len(result) == 1
                    response_data = json.loads(result[0].text)
                    assert response_data["data"] == f"✅ Message saved to Notion page for {today}"
                    assert response_data["error"] == ""

                    # Assert - Notion client interactions use full datetime
                    mock_notion_client.find_page_by_title.assert_called_once_with(
                        "test_parent_page_id_456", "2025-08-05 10:30:45"
                    )
                # Should not create new page since one exists
                mock_notion_client.create_page.assert_not_called()

                # Should append to existing page
                mock_notion_client.append_content_to_page.assert_called_once()
                call_args = mock_notion_client.append_content_to_page.call_args
                assert call_args[0][0] == "existing_page_id_123"

    @pytest.mark.asyncio
    async def test_workflow_with_accumulated_parameters(self, cattackle, mock_notion_client, test_user_config):
        """Test the workflow with accumulated parameters from previous messages."""
        # Arrange
        today = datetime.now().strftime("%Y-%m-%d")
        test_message = "Final message"
        accumulated_params = ["First accumulated message", "Second accumulated message"]

        with patch("notion.config.user_config.USER_CONFIGS", test_user_config):
            with patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client):
                with (
                    patch("notion.core.cattackle.format_date_for_page_title", return_value="2025-08-05 10:30:45"),
                    patch("notion.core.cattackle.get_current_date_iso", return_value=today),
                ):
                    # Page already exists
                    mock_notion_client.find_page_by_title.return_value = "existing_page_id_456"
                    mock_notion_client.append_content_to_page.return_value = None

                    # Act
                    arguments = {"text": test_message, "username": "testuser", "accumulated_params": accumulated_params}
                    result = await handle_tool_call(cattackle, "to_notion", arguments)

                    # Assert - Response format
                    assert len(result) == 1
                    response_data = json.loads(result[0].text)
                assert response_data["data"] == f"✅ Message saved to Notion page for {today}"
                assert response_data["error"] == ""

                # Assert - Content includes accumulated parameters
                mock_notion_client.append_content_to_page.assert_called_once()
                call_args = mock_notion_client.append_content_to_page.call_args
                appended_content = call_args[0][1]  # content

                # Should contain all accumulated messages plus the final message
                assert "First accumulated message" in appended_content
                assert "Second accumulated message" in appended_content
                assert "Final message" in appended_content

    @pytest.mark.asyncio
    async def test_workflow_without_accumulated_parameters(self, cattackle, mock_notion_client, test_user_config):
        """Test the workflow with immediate parameters only (no accumulation)."""
        # Arrange
        today = datetime.now().strftime("%Y-%m-%d")
        test_message = "Immediate message only"

        with patch("notion.config.user_config.USER_CONFIGS", test_user_config):
            with patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client):
                with (
                    patch("notion.core.cattackle.format_date_for_page_title", return_value="2025-08-05 10:30:45"),
                    patch("notion.core.cattackle.get_current_date_iso", return_value=today),
                ):
                    mock_notion_client.find_page_by_title.return_value = "existing_page_id_789"
                    mock_notion_client.append_content_to_page.return_value = None

                    # Act - No accumulated_params provided
                    arguments = {"text": test_message, "username": "testuser"}
                    result = await handle_tool_call(cattackle, "to_notion", arguments)

                    # Assert - Response format
                    assert len(result) == 1
                response_data = json.loads(result[0].text)
                assert response_data["data"] == f"✅ Message saved to Notion page for {today}"

                # Assert - Content contains only the immediate message
                mock_notion_client.append_content_to_page.assert_called_once()
                call_args = mock_notion_client.append_content_to_page.call_args
                appended_content = call_args[0][1]

                # Should contain only the test message (plus timestamp)
                assert test_message in appended_content
                assert "[" in appended_content  # timestamp format

    @pytest.mark.asyncio
    async def test_workflow_unauthorized_user_silent_skip(self, cattackle):
        """Test that unauthorized users are silently skipped without errors."""
        # Arrange - No user configuration provided (empty USER_CONFIGS)
        with patch("notion.config.user_config.USER_CONFIGS", {}):
            # Act
            arguments = {"text": "This should be silently skipped", "username": "unauthorized_user"}
            result = await handle_tool_call(cattackle, "to_notion", arguments)

            # Assert - Silent skip returns empty success response
            assert len(result) == 1
            response_data = json.loads(result[0].text)
            assert response_data["data"] == ""  # Empty data for silent skip
            assert response_data["error"] == ""

    @pytest.mark.asyncio
    async def test_workflow_notion_api_authentication_error(self, cattackle, mock_notion_client, test_user_config):
        """Test workflow handling of Notion API authentication errors."""
        # Arrange
        with patch("notion.config.user_config.USER_CONFIGS", test_user_config):
            with patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client):
                # Mock authentication error
                api_error = NotionAPIResponseBuilder.create_api_error("Authentication failed", 401)
                mock_notion_client.find_page_by_title.side_effect = api_error

                # Act
                arguments = {"text": "Test message", "username": "testuser"}
                result = await handle_tool_call(cattackle, "to_notion", arguments)

                # Assert - Error is handled gracefully
                MCPTestHelper.assert_error_response(result, "Authentication failed")

    @pytest.mark.asyncio
    async def test_workflow_notion_api_timeout_error(self, cattackle, mock_notion_client, test_user_config):
        """Test workflow handling of Notion API timeout errors."""
        # Arrange
        with patch("notion.config.user_config.USER_CONFIGS", test_user_config):
            with patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client):
                # Mock timeout error
                timeout_error = RequestTimeoutError("Request timed out")
                mock_notion_client.find_page_by_title.side_effect = timeout_error

                # Act
                arguments = {"text": "Test message", "username": "testuser"}
                result = await handle_tool_call(cattackle, "to_notion", arguments)

                # Assert - Error is handled gracefully
                MCPTestHelper.assert_error_response(result, "timed out")

    @pytest.mark.asyncio
    async def test_workflow_page_creation_failure_recovery(self, cattackle, mock_notion_client, test_user_config):
        """Test workflow when page creation fails but page lookup succeeds."""
        # Arrange
        with patch("notion.config.user_config.USER_CONFIGS", test_user_config):
            with patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client):
                # First call: page doesn't exist
                # Second call: page creation fails
                # This simulates a race condition where another process created the page
                mock_notion_client.find_page_by_title.return_value = None
                mock_notion_client.create_page.side_effect = NotionAPIResponseBuilder.create_api_error(
                    "Page creation failed", 400
                )

                # Act
                arguments = {"text": "Test message", "username": "testuser"}
                result = await handle_tool_call(cattackle, "to_notion", arguments)

                # Assert - Error is handled
                MCPTestHelper.assert_error_response(result)

    @pytest.mark.asyncio
    async def test_workflow_content_appending_failure(self, cattackle, mock_notion_client, test_user_config):
        """Test workflow when content appending fails."""
        # Arrange
        with patch("notion.config.user_config.USER_CONFIGS", test_user_config):
            with patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client):
                # Page exists
                mock_notion_client.find_page_by_title.return_value = "existing_page_id"
                # Content appending fails
                mock_notion_client.append_content_to_page.side_effect = NotionAPIResponseBuilder.create_api_error(
                    "Content appending failed", 400
                )

                # Act
                arguments = {"text": "Test message", "username": "testuser"}
                result = await handle_tool_call(cattackle, "to_notion", arguments)

                # Assert - Error is handled
                MCPTestHelper.assert_error_response(result)

    @pytest.mark.asyncio
    async def test_workflow_with_empty_message_content(self, cattackle, mock_notion_client, test_user_config):
        """Test workflow with empty message content (should be rejected by validation)."""
        # Arrange
        with patch("notion.config.user_config.USER_CONFIGS", test_user_config):
            with patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client):
                mock_notion_client.find_page_by_title.return_value = "existing_page_id"
                mock_notion_client.append_content_to_page.return_value = None

                # Act - Empty message content (should be rejected)
                arguments = {"text": "", "username": "testuser"}
                result = await handle_tool_call(cattackle, "to_notion", arguments)

                # Assert - Should be rejected by validation
                assert len(result) == 1
                response_data = json.loads(result[0].text)
                assert response_data["data"] == ""
                assert "Either text or accumulated_params must be provided" in response_data["error"]

                # Assert - Content was not appended due to validation failure
                mock_notion_client.append_content_to_page.assert_not_called()

    @pytest.mark.asyncio
    async def test_workflow_with_unicode_content(self, cattackle, mock_notion_client, test_user_config):
        """Test workflow with Unicode characters in message content."""
        # Arrange
        unicode_message = "Test message with emojis 🎉📝 and unicode characters: café, naïve, résumé"

        with patch("notion.config.user_config.USER_CONFIGS", test_user_config):
            with patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client):
                mock_notion_client.find_page_by_title.return_value = "existing_page_id"
                mock_notion_client.append_content_to_page.return_value = None

                # Act
                arguments = {"text": unicode_message, "username": "testuser"}
                result = await handle_tool_call(cattackle, "to_notion", arguments)

                # Assert - Unicode content is handled correctly
                assert len(result) == 1
                response_data = json.loads(result[0].text)
                assert "✅" in response_data["data"]
                assert response_data["error"] == ""

                # Assert - Unicode content was preserved
                mock_notion_client.append_content_to_page.assert_called_once()
                call_args = mock_notion_client.append_content_to_page.call_args
                appended_content = call_args[0][1]
                assert "🎉📝" in appended_content
                assert "café" in appended_content
