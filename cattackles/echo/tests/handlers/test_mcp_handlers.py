"""
Tests for the MCP handlers.
These tests focus on the MCP tool call routing and response formatting.
"""

from unittest.mock import AsyncMock, MagicMock

import mcp.types as types
import pytest

from cattackles.echo.src.core.cattackle import EchoCattackle
from cattackles.echo.src.handlers.mcp_handlers import handle_tool_call


class TestMCPHandlers:
    """Test class for MCP handler functionality."""

    @pytest.fixture
    def mock_cattackle_for_handlers(self):
        """Create a mock cattackle instance specifically for handler tests."""
        cattackle = MagicMock(spec=EchoCattackle)

        # Mock async methods
        cattackle.echo = AsyncMock(return_value='{"data": "echo response", "error": null}')
        cattackle.ping = AsyncMock(return_value='{"data": "pong", "error": null}')
        cattackle.joke = AsyncMock(return_value='{"data": "joke response", "error": null}')

        return cattackle

    @pytest.mark.asyncio
    async def test_handle_echo_tool_call(self, mock_cattackle_for_handlers):
        """Test handling echo tool call."""
        arguments = {"text": "test message", "accumulated_params": ["param1", "param2"]}

        result = await handle_tool_call(mock_cattackle_for_handlers, "echo", arguments)

        # Verify cattackle method was called correctly
        mock_cattackle_for_handlers.echo.assert_called_once_with("test message", ["param1", "param2"])

        # Verify response format
        assert len(result) == 1
        assert isinstance(result[0], types.TextContent)
        assert result[0].type == "text"
        assert result[0].text == '{"data": "echo response", "error": null}'

    @pytest.mark.asyncio
    async def test_handle_ping_tool_call(self, mock_cattackle_for_handlers):
        """Test handling ping tool call."""
        arguments = {"text": "ping test", "accumulated_params": []}

        result = await handle_tool_call(mock_cattackle_for_handlers, "ping", arguments)

        # Verify cattackle method was called correctly
        mock_cattackle_for_handlers.ping.assert_called_once_with("ping test", [])

        # Verify response format
        assert len(result) == 1
        assert isinstance(result[0], types.TextContent)
        assert result[0].type == "text"
        assert result[0].text == '{"data": "pong", "error": null}'

    @pytest.mark.asyncio
    async def test_handle_joke_tool_call(self, mock_cattackle_for_handlers):
        """Test handling joke tool call."""
        arguments = {"text": "cats", "accumulated_params": ["dogs", "birds"]}

        result = await handle_tool_call(mock_cattackle_for_handlers, "joke", arguments)

        # Verify cattackle method was called correctly
        mock_cattackle_for_handlers.joke.assert_called_once_with("cats", ["dogs", "birds"])

        # Verify response format
        assert len(result) == 1
        assert isinstance(result[0], types.TextContent)
        assert result[0].type == "text"
        assert result[0].text == '{"data": "joke response", "error": null}'

    @pytest.mark.asyncio
    async def test_handle_tool_call_missing_arguments(self, mock_cattackle_for_handlers):
        """Test handling tool call with missing arguments."""
        arguments = {}  # Missing text and accumulated_params

        await handle_tool_call(mock_cattackle_for_handlers, "echo", arguments)

        # Should use default values
        mock_cattackle_for_handlers.echo.assert_called_once_with("", [])

    @pytest.mark.asyncio
    async def test_handle_tool_call_partial_arguments(self, mock_cattackle_for_handlers):
        """Test handling tool call with partial arguments."""
        arguments = {"text": "only text"}  # Missing accumulated_params

        await handle_tool_call(mock_cattackle_for_handlers, "echo", arguments)

        # Should use default for missing argument
        mock_cattackle_for_handlers.echo.assert_called_once_with("only text", [])

    @pytest.mark.asyncio
    async def test_handle_unknown_tool_call(self, mock_cattackle_for_handlers):
        """Test handling unknown tool call."""
        arguments = {"text": "test"}

        with pytest.raises(ValueError, match="Unknown tool: unknown_tool"):
            await handle_tool_call(mock_cattackle_for_handlers, "unknown_tool", arguments)

    @pytest.mark.asyncio
    async def test_handle_tool_call_preserves_cattackle_response(self, mock_cattackle_for_handlers):
        """Test that handler preserves the exact response from cattackle."""
        # Set up a specific response
        expected_response = '{"data": "specific response", "error": "some error"}'
        mock_cattackle_for_handlers.echo.return_value = expected_response

        arguments = {"text": "test"}
        result = await handle_tool_call(mock_cattackle_for_handlers, "echo", arguments)

        assert result[0].text == expected_response

    @pytest.mark.asyncio
    async def test_handle_tool_call_with_cattackle_exception(self, mock_cattackle_for_handlers):
        """Test handling tool call when cattackle method raises exception."""
        # Make the cattackle method raise an exception
        mock_cattackle_for_handlers.echo.side_effect = Exception("Cattackle error")

        arguments = {"text": "test"}

        # The exception should propagate up
        with pytest.raises(Exception, match="Cattackle error"):
            await handle_tool_call(mock_cattackle_for_handlers, "echo", arguments)
