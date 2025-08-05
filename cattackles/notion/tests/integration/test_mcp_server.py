"""Integration tests for the MCP server functionality."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from mcp.server.lowlevel import Server
from notion.core.cattackle import NotionCattackle
from notion.handlers.mcp_handlers import handle_tool_call
from notion.handlers.tools import get_tool_definitions
from notion.server import create_mcp_server


class TestMCPServerIntegration:
    """Integration tests for the MCP server."""

    @pytest.fixture
    def mock_cattackle(self):
        """Create a mock NotionCattackle instance."""
        cattackle = MagicMock(spec=NotionCattackle)
        cattackle.save_to_notion = AsyncMock()
        return cattackle

    @pytest.fixture
    def mcp_server(self, mock_cattackle):
        """Create an MCP server instance for testing."""
        return create_mcp_server(mock_cattackle)

    def test_create_mcp_server(self, mock_cattackle):
        """Test that MCP server is created correctly."""
        # Act
        server = create_mcp_server(mock_cattackle)

        # Assert
        assert isinstance(server, Server)
        assert server.name == "notion-cattackle"

    def test_list_tools(self):
        """Test that the server correctly lists available tools."""
        # Act
        tools = get_tool_definitions()

        # Assert
        assert len(tools) == 1
        tool = tools[0]
        assert tool.name == "to_notion"
        assert "Save message content to a daily Notion page" in tool.description

        # Check input schema
        schema = tool.inputSchema
        assert schema["type"] == "object"
        assert "text" in schema["properties"]
        assert "username" in schema["properties"]
        assert "accumulated_params" in schema["properties"]
        assert set(schema["required"]) == {"text", "username"}

    @pytest.mark.asyncio
    async def test_call_tool_to_notion_success(self, mock_cattackle):
        """Test successful tool call through MCP handler."""
        # Arrange
        mock_cattackle.save_to_notion.return_value = "✅ Message saved to Notion page for 2025-01-15"

        arguments = {"text": "Test message", "username": "testuser", "accumulated_params": ["Previous message"]}

        # Act
        result = await handle_tool_call(mock_cattackle, "to_notion", arguments)

        # Assert
        assert len(result) == 1
        assert result[0].type == "text"

        response_data = json.loads(result[0].text)
        assert response_data["data"] == "✅ Message saved to Notion page for 2025-01-15"
        assert response_data["error"] == ""

        # Verify the cattackle was called correctly
        mock_cattackle.save_to_notion.assert_called_once_with(
            username="testuser", message_content="Test message", accumulated_params=["Previous message"]
        )

    @pytest.mark.asyncio
    async def test_call_tool_to_notion_error(self, mock_cattackle):
        """Test tool call error handling through MCP handler."""
        # Arrange
        mock_cattackle.save_to_notion.side_effect = Exception("Notion API error")

        arguments = {"text": "Test message", "username": "testuser"}

        # Act
        result = await handle_tool_call(mock_cattackle, "to_notion", arguments)

        # Assert
        assert len(result) == 1
        response_data = json.loads(result[0].text)
        assert response_data["data"] == ""
        assert "Notion API error" in response_data["error"]

    @pytest.mark.asyncio
    async def test_call_unknown_tool(self, mock_cattackle):
        """Test calling an unknown tool through MCP handler."""
        # Act
        result = await handle_tool_call(mock_cattackle, "unknown_tool", {})

        # Assert
        assert len(result) == 1
        response_data = json.loads(result[0].text)
        assert response_data["data"] == ""
        assert "Unknown tool: unknown_tool" in response_data["error"]

    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, mock_cattackle):
        """Test the complete end-to-end workflow from MCP server creation to tool execution."""
        # Arrange
        mock_cattackle.save_to_notion.return_value = "✅ Message saved successfully"
        create_mcp_server(mock_cattackle)

        # Act - List tools
        tools = get_tool_definitions()

        # Act - Call tool
        arguments = {
            "text": "Integration test message",
            "username": "integration_user",
            "accumulated_params": ["Context message 1", "Context message 2"],
        }
        result = await handle_tool_call(mock_cattackle, "to_notion", arguments)

        # Assert - Tools are listed correctly
        assert len(tools) == 1
        assert tools[0].name == "to_notion"

        # Assert - Tool call works correctly
        assert len(result) == 1
        response_data = json.loads(result[0].text)
        assert response_data["data"] == "✅ Message saved successfully"
        assert response_data["error"] == ""

        # Assert - Core logic was called with correct parameters
        mock_cattackle.save_to_notion.assert_called_once_with(
            username="integration_user",
            message_content="Integration test message",
            accumulated_params=["Context message 1", "Context message 2"],
        )

    @pytest.mark.asyncio
    async def test_json_response_format(self, mock_cattackle):
        """Test that responses are properly formatted as JSON."""
        # Arrange
        mock_cattackle.save_to_notion.return_value = "✅ Success with unicode: 🎉"

        arguments = {"text": "Message with unicode: 📝", "username": "testuser"}

        # Act
        result = await handle_tool_call(mock_cattackle, "to_notion", arguments)

        # Assert
        assert len(result) == 1
        response_text = result[0].text

        # Verify it's valid JSON
        response_data = json.loads(response_text)
        assert isinstance(response_data, dict)
        assert "data" in response_data
        assert "error" in response_data

        # Verify unicode is preserved
        assert "🎉" in response_data["data"]

    def test_server_configuration(self, mock_cattackle):
        """Test that the MCP server is properly configured with handlers."""
        # Act
        server = create_mcp_server(mock_cattackle)

        # Assert
        assert isinstance(server, Server)
        assert server.name == "notion-cattackle"

        # Verify that handlers are registered (we can't directly test the handlers
        # but we can verify the server was created successfully)
        assert server is not None
