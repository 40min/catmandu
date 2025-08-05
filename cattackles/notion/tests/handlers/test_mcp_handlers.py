"""Tests for MCP handlers in the Notion cattackle."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from notion.core.cattackle import NotionCattackle
from notion.handlers.mcp_handlers import handle_tool_call


class TestMCPHandlers:
    """Test cases for MCP tool call handlers."""

    @pytest.fixture
    def mock_cattackle(self):
        """Create a mock NotionCattackle instance."""
        cattackle = MagicMock(spec=NotionCattackle)
        cattackle.save_to_notion = AsyncMock()
        return cattackle

    @pytest.mark.asyncio
    async def test_handle_to_notion_success(self, mock_cattackle):
        """Test successful to_notion command handling."""
        # Arrange
        mock_cattackle.save_to_notion.return_value = "✅ Message saved to Notion page for 2025-01-15"

        arguments = {"text": "Test message content", "username": "testuser", "accumulated_params": ["Previous message"]}

        # Act
        result = await handle_tool_call(mock_cattackle, "to_notion", arguments)

        # Assert
        assert len(result) == 1
        assert result[0].type == "text"

        response_data = json.loads(result[0].text)
        assert response_data["data"] == "✅ Message saved to Notion page for 2025-01-15"
        assert response_data["error"] == ""

        # Verify the cattackle method was called correctly
        mock_cattackle.save_to_notion.assert_called_once_with(
            username="testuser", message_content="Test message content", accumulated_params=["Previous message"]
        )

    @pytest.mark.asyncio
    async def test_handle_to_notion_without_accumulated_params(self, mock_cattackle):
        """Test to_notion command handling without accumulated parameters."""
        # Arrange
        mock_cattackle.save_to_notion.return_value = "✅ Message saved to Notion page for 2025-01-15"

        arguments = {"text": "Test message content", "username": "testuser"}

        # Act
        result = await handle_tool_call(mock_cattackle, "to_notion", arguments)

        # Assert
        assert len(result) == 1
        response_data = json.loads(result[0].text)
        assert response_data["data"] == "✅ Message saved to Notion page for 2025-01-15"
        assert response_data["error"] == ""

        # Verify the cattackle method was called with None for accumulated_params
        mock_cattackle.save_to_notion.assert_called_once_with(
            username="testuser", message_content="Test message content", accumulated_params=None
        )

    @pytest.mark.asyncio
    async def test_handle_to_notion_missing_username(self, mock_cattackle):
        """Test to_notion command handling with missing username."""
        # Arrange
        arguments = {"text": "Test message content"}

        # Act
        result = await handle_tool_call(mock_cattackle, "to_notion", arguments)

        # Assert
        assert len(result) == 1
        response_data = json.loads(result[0].text)
        assert response_data["data"] == ""
        assert "Username is required" in response_data["error"]

        # Verify the cattackle method was not called
        mock_cattackle.save_to_notion.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_to_notion_missing_text_and_params(self, mock_cattackle):
        """Test to_notion command handling with missing text and accumulated params."""
        # Arrange
        arguments = {"username": "testuser"}

        # Act
        result = await handle_tool_call(mock_cattackle, "to_notion", arguments)

        # Assert
        assert len(result) == 1
        response_data = json.loads(result[0].text)
        assert response_data["data"] == ""
        assert "Either text or accumulated_params must be provided" in response_data["error"]

        # Verify the cattackle method was not called
        mock_cattackle.save_to_notion.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_to_notion_with_empty_accumulated_params(self, mock_cattackle):
        """Test to_notion command handling with empty accumulated params list."""
        # Arrange
        mock_cattackle.save_to_notion.return_value = "✅ Message saved to Notion page for 2025-01-15"

        arguments = {"text": "Test message content", "username": "testuser", "accumulated_params": []}

        # Act
        result = await handle_tool_call(mock_cattackle, "to_notion", arguments)

        # Assert
        assert len(result) == 1
        response_data = json.loads(result[0].text)
        assert response_data["data"] == "✅ Message saved to Notion page for 2025-01-15"
        assert response_data["error"] == ""

        # Verify the cattackle method was called with None for empty accumulated_params
        mock_cattackle.save_to_notion.assert_called_once_with(
            username="testuser", message_content="Test message content", accumulated_params=None
        )

    @pytest.mark.asyncio
    async def test_handle_to_notion_cattackle_error(self, mock_cattackle):
        """Test to_notion command handling when cattackle raises an error."""
        # Arrange
        mock_cattackle.save_to_notion.side_effect = Exception("Notion API error")

        arguments = {"text": "Test message content", "username": "testuser"}

        # Act
        result = await handle_tool_call(mock_cattackle, "to_notion", arguments)

        # Assert
        assert len(result) == 1
        response_data = json.loads(result[0].text)
        assert response_data["data"] == ""
        assert "Notion API error" in response_data["error"]

    @pytest.mark.asyncio
    async def test_handle_unknown_tool(self, mock_cattackle):
        """Test handling of unknown tool names."""
        # Arrange
        arguments = {"text": "test"}

        # Act
        result = await handle_tool_call(mock_cattackle, "unknown_tool", arguments)

        # Assert
        assert len(result) == 1
        response_data = json.loads(result[0].text)
        assert response_data["data"] == ""
        assert "Unknown tool: unknown_tool" in response_data["error"]

    @pytest.mark.asyncio
    async def test_handle_to_notion_only_accumulated_params(self, mock_cattackle):
        """Test to_notion command handling with only accumulated parameters (no immediate text)."""
        # Arrange
        mock_cattackle.save_to_notion.return_value = "✅ Message saved to Notion page for 2025-01-15"

        arguments = {
            "text": "",  # Empty text
            "username": "testuser",
            "accumulated_params": ["Accumulated message 1", "Accumulated message 2"],
        }

        # Act
        result = await handle_tool_call(mock_cattackle, "to_notion", arguments)

        # Assert
        assert len(result) == 1
        response_data = json.loads(result[0].text)
        assert response_data["data"] == "✅ Message saved to Notion page for 2025-01-15"
        assert response_data["error"] == ""

        # Verify the cattackle method was called correctly
        mock_cattackle.save_to_notion.assert_called_once_with(
            username="testuser",
            message_content="",
            accumulated_params=["Accumulated message 1", "Accumulated message 2"],
        )
