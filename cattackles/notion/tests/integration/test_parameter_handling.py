"""Integration tests for parameter handling scenarios.

These tests focus specifically on how the cattackle handles different
parameter scenarios: immediate parameters only vs accumulated parameters
from previous messages.
"""

from unittest.mock import patch

import pytest
from notion.core.cattackle import NotionCattackle
from notion.handlers.mcp_handlers import handle_tool_call

from .test_utilities import (
    ContentTestHelper,
    IntegrationTestScenario,
    MCPTestHelper,
    MockNotionClientBuilder,
    UserConfigBuilder,
)


class TestParameterHandling:
    """Integration tests for different parameter handling scenarios."""

    @pytest.fixture
    def cattackle(self):
        """Create a NotionCattackle instance for testing."""
        return NotionCattackle()

    @pytest.mark.asyncio
    async def test_immediate_parameters_only(self, cattackle):
        """Test handling of immediate parameters without accumulation."""
        # Arrange
        user_config, mock_notion_client = IntegrationTestScenario.existing_page_scenario()
        test_message = "This is an immediate message"

        with patch("notion.config.user_config.USER_CONFIGS", user_config):
            with patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client):
                # Act
                arguments = MCPTestHelper.create_mcp_arguments(
                    text=test_message,
                    username="testuser",
                    # No accumulated_params provided
                )
                result = await handle_tool_call(cattackle, "to_notion", arguments)

                # Assert - Success response
                MCPTestHelper.assert_success_response(result)

                # Assert - Content contains only the immediate message
                mock_notion_client.append_content_to_page.assert_called_once()
                call_args = mock_notion_client.append_content_to_page.call_args
                appended_content = call_args[0][1]  # content parameter

                # Should contain the test message and timestamp
                ContentTestHelper.assert_content_contains_timestamp(appended_content)
                ContentTestHelper.assert_content_contains_all_parts(appended_content, [test_message])

                # Should NOT contain any accumulated content indicators
                assert "Accumulated" not in appended_content

    @pytest.mark.asyncio
    async def test_accumulated_parameters_with_immediate(self, cattackle):
        """Test handling of accumulated parameters combined with immediate message."""
        # Arrange
        user_config, mock_notion_client = IntegrationTestScenario.existing_page_scenario()
        immediate_message = "Final command message"
        accumulated_params = ContentTestHelper.create_accumulated_params(3)

        with patch("notion.config.user_config.USER_CONFIGS", user_config):
            with patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client):
                # Act
                arguments = MCPTestHelper.create_mcp_arguments(
                    text=immediate_message, username="testuser", accumulated_params=accumulated_params
                )
                result = await handle_tool_call(cattackle, "to_notion", arguments)

                # Assert - Success response
                MCPTestHelper.assert_success_response(result)

                # Assert - Content contains both accumulated and immediate messages
                mock_notion_client.append_content_to_page.assert_called_once()
                call_args = mock_notion_client.append_content_to_page.call_args
                appended_content = call_args[0][1]  # content parameter

                # Should contain timestamp
                ContentTestHelper.assert_content_contains_timestamp(appended_content)

                # Should contain all accumulated messages
                expected_parts = accumulated_params + [immediate_message]
                ContentTestHelper.assert_content_contains_all_parts(appended_content, expected_parts)

                # Verify the order: accumulated messages should come before immediate message
                immediate_pos = appended_content.find(immediate_message)
                for acc_msg in accumulated_params:
                    acc_pos = appended_content.find(acc_msg)
                    assert (
                        acc_pos < immediate_pos
                    ), f"Accumulated message '{acc_msg}' should come before immediate message"

    @pytest.mark.asyncio
    async def test_empty_accumulated_parameters(self, cattackle):
        """Test handling when accumulated_params is provided but empty."""
        # Arrange
        user_config, mock_notion_client = IntegrationTestScenario.existing_page_scenario()
        immediate_message = "Message with empty accumulation"

        with patch("notion.config.user_config.USER_CONFIGS", user_config):
            with patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client):
                # Act
                arguments = MCPTestHelper.create_mcp_arguments(
                    text=immediate_message, username="testuser", accumulated_params=[]  # Empty list
                )
                result = await handle_tool_call(cattackle, "to_notion", arguments)

                # Assert - Success response
                MCPTestHelper.assert_success_response(result)

                # Assert - Content contains only the immediate message
                mock_notion_client.append_content_to_page.assert_called_once()
                call_args = mock_notion_client.append_content_to_page.call_args
                appended_content = call_args[0][1]

                # Should contain only the immediate message (plus timestamp)
                ContentTestHelper.assert_content_contains_timestamp(appended_content)
                assert immediate_message in appended_content

                # Should not have extra spaces from empty accumulation
                assert "  " not in appended_content.replace("[", "").replace("]", "")  # Ignore timestamp brackets

    @pytest.mark.asyncio
    async def test_accumulated_parameters_with_empty_immediate(self, cattackle):
        """Test handling when immediate message is empty but accumulated params exist."""
        # Arrange
        user_config, mock_notion_client = IntegrationTestScenario.existing_page_scenario()
        accumulated_params = ["First accumulated", "Second accumulated"]

        with patch("notion.config.user_config.USER_CONFIGS", user_config):
            with patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client):
                # Act
                arguments = MCPTestHelper.create_mcp_arguments(
                    text="", username="testuser", accumulated_params=accumulated_params  # Empty immediate message
                )
                result = await handle_tool_call(cattackle, "to_notion", arguments)

                # Assert - Success response
                MCPTestHelper.assert_success_response(result)

                # Assert - Content contains accumulated messages
                mock_notion_client.append_content_to_page.assert_called_once()
                call_args = mock_notion_client.append_content_to_page.call_args
                appended_content = call_args[0][1]

                # Should contain timestamp and accumulated messages
                ContentTestHelper.assert_content_contains_timestamp(appended_content)
                ContentTestHelper.assert_content_contains_all_parts(appended_content, accumulated_params)

    @pytest.mark.asyncio
    async def test_large_accumulated_parameters(self, cattackle):
        """Test handling of many accumulated parameters."""
        # Arrange
        user_config, mock_notion_client = IntegrationTestScenario.existing_page_scenario()
        immediate_message = "Final message after many accumulated"
        # Create many accumulated parameters
        accumulated_params = [f"Accumulated message number {i+1}" for i in range(10)]

        with patch("notion.config.user_config.USER_CONFIGS", user_config):
            with patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client):
                # Act
                arguments = MCPTestHelper.create_mcp_arguments(
                    text=immediate_message, username="testuser", accumulated_params=accumulated_params
                )
                result = await handle_tool_call(cattackle, "to_notion", arguments)

                # Assert - Success response
                MCPTestHelper.assert_success_response(result)

                # Assert - All content is preserved
                mock_notion_client.append_content_to_page.assert_called_once()
                call_args = mock_notion_client.append_content_to_page.call_args
                appended_content = call_args[0][1]

                # Should contain all accumulated messages and immediate message
                all_expected = accumulated_params + [immediate_message]
                ContentTestHelper.assert_content_contains_all_parts(appended_content, all_expected)

    @pytest.mark.asyncio
    async def test_accumulated_parameters_with_unicode(self, cattackle):
        """Test handling of accumulated parameters containing Unicode characters."""
        # Arrange
        user_config, mock_notion_client = IntegrationTestScenario.existing_page_scenario()
        immediate_message = "Final message 🎉"
        accumulated_params = [
            "First message with café ☕",
            "Second message with résumé 📄",
            "Third message with naïve 🤔",
        ]

        with patch("notion.config.user_config.USER_CONFIGS", user_config):
            with patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client):
                # Act
                arguments = MCPTestHelper.create_mcp_arguments(
                    text=immediate_message, username="testuser", accumulated_params=accumulated_params
                )
                result = await handle_tool_call(cattackle, "to_notion", arguments)

                # Assert - Success response
                MCPTestHelper.assert_success_response(result)

                # Assert - Unicode content is preserved
                mock_notion_client.append_content_to_page.assert_called_once()
                call_args = mock_notion_client.append_content_to_page.call_args
                appended_content = call_args[0][1]

                # Should contain all Unicode characters
                unicode_chars = ["☕", "📄", "🤔", "🎉", "café", "résumé", "naïve"]
                ContentTestHelper.assert_content_contains_all_parts(appended_content, unicode_chars)

    @pytest.mark.asyncio
    async def test_accumulated_parameters_content_ordering(self, cattackle):
        """Test that accumulated parameters maintain correct ordering."""
        # Arrange
        user_config, mock_notion_client = IntegrationTestScenario.existing_page_scenario()
        immediate_message = "IMMEDIATE"
        accumulated_params = ["FIRST", "SECOND", "THIRD"]

        with patch("notion.config.user_config.USER_CONFIGS", user_config):
            with patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client):
                # Act
                arguments = MCPTestHelper.create_mcp_arguments(
                    text=immediate_message, username="testuser", accumulated_params=accumulated_params
                )
                result = await handle_tool_call(cattackle, "to_notion", arguments)

                # Assert - Success response
                MCPTestHelper.assert_success_response(result)

                # Assert - Content ordering is correct
                mock_notion_client.append_content_to_page.assert_called_once()
                call_args = mock_notion_client.append_content_to_page.call_args
                appended_content = call_args[0][1]

                # Find positions of each message
                first_pos = appended_content.find("FIRST")
                second_pos = appended_content.find("SECOND")
                third_pos = appended_content.find("THIRD")
                immediate_pos = appended_content.find("IMMEDIATE")

                # Verify ordering: FIRST < SECOND < THIRD < IMMEDIATE
                assert (
                    first_pos < second_pos < third_pos < immediate_pos
                ), f"Content ordering is incorrect: {appended_content}"

    @pytest.mark.asyncio
    async def test_parameter_handling_with_whitespace(self, cattackle):
        """Test parameter handling with various whitespace scenarios."""
        # Arrange
        user_config, mock_notion_client = IntegrationTestScenario.existing_page_scenario()
        immediate_message = "  Final message with spaces  "
        accumulated_params = ["  First with leading spaces", "Second with trailing spaces  ", "  Third with both  "]

        with patch("notion.config.user_config.USER_CONFIGS", user_config):
            with patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client):
                # Act
                arguments = MCPTestHelper.create_mcp_arguments(
                    text=immediate_message, username="testuser", accumulated_params=accumulated_params
                )
                result = await handle_tool_call(cattackle, "to_notion", arguments)

                # Assert - Success response
                MCPTestHelper.assert_success_response(result)

                # Assert - Whitespace is handled appropriately
                mock_notion_client.append_content_to_page.assert_called_once()
                call_args = mock_notion_client.append_content_to_page.call_args
                appended_content = call_args[0][1]

                # Content should be properly joined (strip() is applied in the core logic)
                # The exact whitespace handling depends on implementation, but content should be readable
                assert "First with leading spaces" in appended_content
                assert "Second with trailing spaces" in appended_content
                assert "Third with both" in appended_content
                assert "Final message with spaces" in appended_content

    @pytest.mark.asyncio
    async def test_parameter_handling_error_scenarios(self, cattackle):
        """Test parameter handling when errors occur during processing."""
        # Arrange
        user_config = UserConfigBuilder().add_test_user("testuser").build()
        mock_notion_client = (
            MockNotionClientBuilder()
            .with_existing_page("test_parent_page_id_testuser", "2025-01-15", "existing_page")
            .with_content_append_error(Exception("Content append failed"))
            .build()
        )

        accumulated_params = ["Accumulated message 1", "Accumulated message 2"]
        immediate_message = "This should fail"

        with patch("notion.config.user_config.USER_CONFIGS", user_config):
            with patch("notion.core.cattackle.NotionClientWrapper", return_value=mock_notion_client):
                # Act
                arguments = MCPTestHelper.create_mcp_arguments(
                    text=immediate_message, username="testuser", accumulated_params=accumulated_params
                )
                result = await handle_tool_call(cattackle, "to_notion", arguments)

                # Assert - Error response
                MCPTestHelper.assert_error_response(result)

                # Assert - The combined content was attempted to be appended
                mock_notion_client.append_content_to_page.assert_called_once()
                call_args = mock_notion_client.append_content_to_page.call_args
                attempted_content = call_args[0][1]

                # Should have tried to append the combined content
                assert "Accumulated message 1" in attempted_content
                assert "Accumulated message 2" in attempted_content
                assert immediate_message in attempted_content
