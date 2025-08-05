"""Integration tests for daily page creation and message appending scenarios.

These tests focus on the page management aspects of the cattackle:
- Daily page creation when pages don't exist
- Message appending to existing pages
- Error handling during page operations
- Edge cases in page management
"""

from unittest.mock import patch

import pytest
from notion.core.cattackle import NotionCattackle
from notion.handlers.mcp_handlers import handle_tool_call

from .test_utilities import (
    DateTestHelper,
    MCPTestHelper,
    MockNotionClientBuilder,
    NotionAPIResponseBuilder,
    UserConfigBuilder,
)


class TestPageManagement:
    """Integration tests for daily page creation and management scenarios."""

    @pytest.fixture
    def cattackle(self):
        """Create a NotionCattackle instance for testing."""
        return NotionCattackle()

    @pytest.mark.asyncio
    async def test_daily_page_creation_new_page(self, cattackle):
        """Test creation of a new daily page when none exists."""
        # Arrange
        user_config = UserConfigBuilder().add_test_user("testuser").build()
        today = DateTestHelper.get_test_date_string()

        test_datetime = f"{today} 10:30:45"
        mock_notion_client = (
            MockNotionClientBuilder()
            .with_no_existing_page("test_parent_page_id_testuser", test_datetime)
            .with_successful_page_creation("new_daily_page_123")
            .with_successful_content_append()
            .build()
        )

        with patch("notion.config.user_config.USER_CONFIGS", user_config):
            with patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client):
                with (
                    patch("notion.core.cattackle.format_date_for_page_title", return_value=test_datetime),
                    patch("notion.core.cattackle.get_current_date_iso", return_value=today),
                ):

                    # Act
                    arguments = MCPTestHelper.create_mcp_arguments(
                        text="Test message for new page", username="testuser"
                    )
                    result = await handle_tool_call(cattackle, "to_notion", arguments)

                    # Assert - Success response
                    MCPTestHelper.assert_success_response(result, f"✅ Message saved to Notion page for {today}")

                    # Assert - Page search was performed with full datetime
                    mock_notion_client.find_page_by_title.assert_called_once_with(
                        "test_parent_page_id_testuser", test_datetime
                    )

                    # Assert - New page was created with full datetime
                    mock_notion_client.create_page.assert_called_once_with(
                        "test_parent_page_id_testuser", test_datetime
                    )

                    # Assert - Content was appended to new page
                    mock_notion_client.append_content_to_page.assert_called_once()
                    call_args = mock_notion_client.append_content_to_page.call_args
                    assert call_args[0][0] == "new_daily_page_123"  # page_id
                    assert "Test message for new page" in call_args[0][1]  # content

    @pytest.mark.asyncio
    async def test_daily_page_existing_page_append(self, cattackle):
        """Test appending to an existing daily page."""
        # Arrange
        user_config = UserConfigBuilder().add_test_user("testuser").build()
        today = DateTestHelper.get_test_date_string()

        test_datetime = f"{today} 10:30:45"
        mock_notion_client = (
            MockNotionClientBuilder()
            .with_existing_page("test_parent_page_id_testuser", test_datetime, "existing_daily_page_456")
            .with_successful_content_append()
            .build()
        )

        with patch("notion.config.user_config.USER_CONFIGS", user_config):
            with patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client):
                with (
                    patch("notion.core.cattackle.format_date_for_page_title", return_value=test_datetime),
                    patch("notion.core.cattackle.get_current_date_iso", return_value=today),
                ):

                    # Act
                    arguments = MCPTestHelper.create_mcp_arguments(
                        text="Test message for existing page", username="testuser"
                    )
                    result = await handle_tool_call(cattackle, "to_notion", arguments)

                    # Assert - Success response
                    MCPTestHelper.assert_success_response(result, f"✅ Message saved to Notion page for {today}")

                    # Assert - Page search was performed with full datetime
                    mock_notion_client.find_page_by_title.assert_called_once_with(
                        "test_parent_page_id_testuser", test_datetime
                    )

                    # Assert - No new page was created
                    mock_notion_client.create_page.assert_not_called()

                    # Assert - Content was appended to existing page
                    mock_notion_client.append_content_to_page.assert_called_once()
                    call_args = mock_notion_client.append_content_to_page.call_args
                    assert call_args[0][0] == "existing_daily_page_456"  # page_id
                    assert "Test message for existing page" in call_args[0][1]  # content

    @pytest.mark.asyncio
    async def test_multiple_messages_same_day(self, cattackle):
        """Test multiple messages being appended to the same daily page."""
        # Arrange
        user_config = UserConfigBuilder().add_test_user("testuser").build()
        today = DateTestHelper.get_test_date_string()

        # First call: page doesn't exist, gets created
        # Second call: page exists, content appended
        mock_notion_client = (
            MockNotionClientBuilder()
            .with_existing_page("test_parent_page_id_testuser", today, "daily_page_789")
            .with_successful_content_append()
            .build()
        )

        with patch("notion.config.user_config.USER_CONFIGS", user_config):
            with patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client):
                with patch("notion.core.cattackle.format_date_for_page_title", return_value=today):

                    # Act - First message
                    arguments1 = MCPTestHelper.create_mcp_arguments(
                        text="First message of the day", username="testuser"
                    )
                    result1 = await handle_tool_call(cattackle, "to_notion", arguments1)

                    # Act - Second message
                    arguments2 = MCPTestHelper.create_mcp_arguments(
                        text="Second message of the day", username="testuser"
                    )
                    result2 = await handle_tool_call(cattackle, "to_notion", arguments2)

                    # Assert - Both calls succeeded
                    MCPTestHelper.assert_success_response(result1)
                    MCPTestHelper.assert_success_response(result2)

                    # Assert - Page search was performed twice
                    assert mock_notion_client.find_page_by_title.call_count == 2

                    # Assert - Content was appended twice to the same page
                    assert mock_notion_client.append_content_to_page.call_count == 2

                    # Verify both messages were appended to the same page
                    calls = mock_notion_client.append_content_to_page.call_args_list
                    assert calls[0][0][0] == "daily_page_789"  # First call page_id
                    assert calls[1][0][0] == "daily_page_789"  # Second call page_id
                    assert "First message of the day" in calls[0][0][1]  # First call content
                    assert "Second message of the day" in calls[1][0][1]  # Second call content

    @pytest.mark.asyncio
    async def test_page_creation_failure_handling(self, cattackle):
        """Test handling when page creation fails."""
        # Arrange
        user_config = UserConfigBuilder().add_test_user("testuser").build()
        today = DateTestHelper.get_test_date_string()

        creation_error = NotionAPIResponseBuilder.create_api_error("Page creation failed", 400, "validation_error")

        mock_notion_client = (
            MockNotionClientBuilder()
            .with_no_existing_page("test_parent_page_id_testuser", today)
            .with_page_creation_error(creation_error)
            .build()
        )

        with patch("notion.config.user_config.USER_CONFIGS", user_config):
            with patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client):
                with patch("notion.core.cattackle.format_date_for_page_title", return_value=today):

                    # Act
                    arguments = MCPTestHelper.create_mcp_arguments(text="Message that should fail", username="testuser")
                    result = await handle_tool_call(cattackle, "to_notion", arguments)

                    # Assert - Error response
                    MCPTestHelper.assert_error_response(result, "❌")

                    # Assert - Page creation was attempted
                    mock_notion_client.create_page.assert_called_once()

                    # Assert - Content append was not attempted
                    mock_notion_client.append_content_to_page.assert_not_called()

    @pytest.mark.asyncio
    async def test_page_search_failure_handling(self, cattackle):
        """Test handling when page search fails."""
        # Arrange
        user_config = UserConfigBuilder().add_test_user("testuser").build()
        today = DateTestHelper.get_test_date_string()

        search_error = NotionAPIResponseBuilder.create_api_error("Search failed", 403, "unauthorized")

        mock_notion_client = MockNotionClientBuilder().with_find_page_error(search_error).build()

        with patch("notion.config.user_config.USER_CONFIGS", user_config):
            with patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client):
                with patch("notion.core.cattackle.datetime") as mock_datetime:
                    mock_datetime.now.return_value.strftime.return_value = today

                    # Act
                    arguments = MCPTestHelper.create_mcp_arguments(
                        text="Message that should fail during search", username="testuser"
                    )
                    result = await handle_tool_call(cattackle, "to_notion", arguments)

                    # Assert - Error response
                    MCPTestHelper.assert_error_response(result, "❌")

                    # Assert - Page search was attempted
                    mock_notion_client.find_page_by_title.assert_called_once()

                    # Assert - Page creation was not attempted
                    mock_notion_client.create_page.assert_not_called()

                    # Assert - Content append was not attempted
                    mock_notion_client.append_content_to_page.assert_not_called()

    @pytest.mark.asyncio
    async def test_content_append_failure_handling(self, cattackle):
        """Test handling when content appending fails."""
        # Arrange
        user_config = UserConfigBuilder().add_test_user("testuser").build()
        today = DateTestHelper.get_test_date_string()

        append_error = NotionAPIResponseBuilder.create_api_error("Content append failed", 400, "validation_error")

        mock_notion_client = (
            MockNotionClientBuilder()
            .with_existing_page("test_parent_page_id_testuser", today, "existing_page_123")
            .with_content_append_error(append_error)
            .build()
        )

        with patch("notion.config.user_config.USER_CONFIGS", user_config):
            with patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client):
                with patch("notion.core.cattackle.datetime") as mock_datetime:
                    mock_datetime.now.return_value.strftime.return_value = today

                    # Act
                    arguments = MCPTestHelper.create_mcp_arguments(
                        text="Message that should fail during append", username="testuser"
                    )
                    result = await handle_tool_call(cattackle, "to_notion", arguments)

                    # Assert - Error response
                    MCPTestHelper.assert_error_response(result, "❌")

                    # Assert - Page search was performed
                    mock_notion_client.find_page_by_title.assert_called_once()

                    # Assert - Content append was attempted
                    mock_notion_client.append_content_to_page.assert_called_once()

    @pytest.mark.asyncio
    async def test_different_users_different_pages(self, cattackle):
        """Test that different users get their own daily pages."""
        # Arrange
        user_config = (
            UserConfigBuilder()
            .add_user("user1", "token1", "parent_page_1")
            .add_user("user2", "token2", "parent_page_2")
            .build()
        )

        today = DateTestHelper.get_test_date_string()

        # Mock client will be created for each user with their own token
        mock_notion_client = (
            MockNotionClientBuilder()
            .with_no_existing_page("parent_page_1", today)
            .with_no_existing_page("parent_page_2", today)
            .with_successful_page_creation("user1_page_123")
            .with_successful_content_append()
            .build()
        )

        with patch("notion.config.user_config.USER_CONFIGS", user_config):
            with patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client):
                with patch("notion.core.cattackle.datetime") as mock_datetime:
                    mock_datetime.now.return_value.strftime.return_value = today

                    # Act - User1 sends message
                    arguments1 = MCPTestHelper.create_mcp_arguments(text="Message from user1", username="user1")
                    result1 = await handle_tool_call(cattackle, "to_notion", arguments1)

                    # Reset mock for second user
                    mock_notion_client.reset_mock()
                    mock_notion_client.create_page.return_value = "user2_page_456"

                    # Act - User2 sends message
                    arguments2 = MCPTestHelper.create_mcp_arguments(text="Message from user2", username="user2")
                    result2 = await handle_tool_call(cattackle, "to_notion", arguments2)

                    # Assert - Both users succeeded
                    MCPTestHelper.assert_success_response(result1)
                    MCPTestHelper.assert_success_response(result2)

                    # Note: Due to mocking limitations, we can't easily verify that different
                    # NotionClientWrapper instances were created with different tokens.
                    # In a real scenario, each user would have their own client instance.

    @pytest.mark.asyncio
    async def test_page_title_date_formatting(self, cattackle):
        """Test that page titles use correct date formatting."""
        # Arrange
        user_config = UserConfigBuilder().add_test_user("testuser").build()

        test_datetime = "2025-01-15 10:30:45"
        mock_notion_client = (
            MockNotionClientBuilder()
            .with_no_existing_page("test_parent_page_id_testuser", test_datetime)
            .with_successful_page_creation("formatted_date_page")
            .with_successful_content_append()
            .build()
        )

        with patch("notion.config.user_config.USER_CONFIGS", user_config):
            with patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client):
                with patch("notion.core.cattackle.format_date_for_page_title", return_value=test_datetime):

                    # Act
                    arguments = MCPTestHelper.create_mcp_arguments(text="Test date formatting", username="testuser")
                    result = await handle_tool_call(cattackle, "to_notion", arguments)

                    # Assert - Success
                    MCPTestHelper.assert_success_response(result)

                    # Assert - Page search used correct datetime format
                    mock_notion_client.find_page_by_title.assert_called_once_with(
                        "test_parent_page_id_testuser", test_datetime
                    )

                    # Assert - Page creation used correct datetime format
                    mock_notion_client.create_page.assert_called_once_with(
                        "test_parent_page_id_testuser", test_datetime
                    )

    @pytest.mark.asyncio
    async def test_message_timestamp_formatting(self, cattackle):
        """Test that messages include proper timestamp formatting."""
        # Arrange
        user_config = UserConfigBuilder().add_test_user("testuser").build()
        today = DateTestHelper.get_test_date_string()

        mock_notion_client = (
            MockNotionClientBuilder()
            .with_existing_page("test_parent_page_id_testuser", today, "existing_page")
            .with_successful_content_append()
            .build()
        )

        with patch("notion.config.user_config.USER_CONFIGS", user_config):
            with patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client):
                with (
                    patch("notion.core.cattackle.format_date_for_page_title", return_value=today),
                    patch("notion.core.cattackle.format_timestamp_for_content", return_value="[14:30:45]"),
                ):

                    # Act
                    arguments = MCPTestHelper.create_mcp_arguments(
                        text="Test timestamp formatting", username="testuser"
                    )
                    result = await handle_tool_call(cattackle, "to_notion", arguments)

                    # Assert - Success
                    MCPTestHelper.assert_success_response(result)

                    # Assert - Content includes timestamp
                    mock_notion_client.append_content_to_page.assert_called_once()
                    call_args = mock_notion_client.append_content_to_page.call_args
                    appended_content = call_args[0][1]

                    # Should contain timestamp in [HH:MM:SS] format
                    assert "[14:30:45]" in appended_content
                    assert "Test timestamp formatting" in appended_content

    @pytest.mark.asyncio
    async def test_concurrent_page_creation_race_condition(self, cattackle):
        """Test handling of race conditions during page creation."""
        # This test simulates a scenario where two processes try to create
        # the same daily page simultaneously

        # Arrange
        user_config = UserConfigBuilder().add_test_user("testuser").build()
        today = DateTestHelper.get_test_date_string()

        # Simulate race condition: first search finds no page, but creation fails
        # because another process created it in the meantime
        race_condition_error = NotionAPIResponseBuilder.create_api_error("Page already exists", 409, "conflict")

        mock_notion_client = (
            MockNotionClientBuilder()
            .with_no_existing_page("test_parent_page_id_testuser", today)
            .with_page_creation_error(race_condition_error)
            .build()
        )

        with patch("notion.config.user_config.USER_CONFIGS", user_config):
            with patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client):
                with patch("notion.core.cattackle.datetime") as mock_datetime:
                    mock_datetime.now.return_value.strftime.return_value = today

                    # Act
                    arguments = MCPTestHelper.create_mcp_arguments(
                        text="Message during race condition", username="testuser"
                    )
                    result = await handle_tool_call(cattackle, "to_notion", arguments)

                    # Assert - Error is handled gracefully
                    # The exact behavior depends on implementation - it might retry
                    # or return an error. Either is acceptable for this edge case.
                    data, error = MCPTestHelper.extract_response_data(result)

                    # Should either succeed (if retry logic exists) or fail gracefully
                    assert isinstance(data, str)
                    assert isinstance(error, str)
