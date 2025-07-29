"""Tests for MCP client."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from catmandu.core.clients.mcp import McpClient
from catmandu.core.errors import CattackleExecutionError
from catmandu.core.models import (
    HttpTransportConfig,
    StdioTransportConfig,
    WebSocketTransportConfig,
)


@pytest.fixture
def mcp_client():
    """Create an MCP client instance."""
    return McpClient()


@pytest.fixture
def stdio_transport_config():
    """Create a sample STDIO transport configuration."""
    return StdioTransportConfig(
        type="stdio",
        command="python",
        args=["-m", "test.server"],
        env={"TEST": "true"},
        cwd=".",
    )


@pytest.fixture
def websocket_transport_config():
    """Create a sample WebSocket transport configuration."""
    return WebSocketTransportConfig(
        type="websocket",
        url="ws://localhost:8080/mcp",
        headers={"Authorization": "Bearer test-token"},
    )


@pytest.fixture
def http_transport_config():
    """Create a sample HTTP transport configuration."""
    return HttpTransportConfig(
        type="http",
        url="http://localhost:8080/mcp",
        headers={"Authorization": "Bearer test-token"},
    )


@pytest.mark.asyncio
async def test_call_tool_success(mcp_client):
    """Test successful tool call."""
    mock_session = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="success")]
    mock_session.call_tool.return_value = mock_response

    response = await mcp_client.call_tool(
        session=mock_session, tool_name="echo", arguments={"message": "test"}, timeout=10.0
    )

    assert response == mock_response
    mock_session.call_tool.assert_called_once_with("echo", {"message": "test"})


@pytest.mark.asyncio
async def test_call_tool_timeout(mcp_client):
    """Test tool call timeout."""
    mock_session = AsyncMock()
    mock_session.call_tool.side_effect = asyncio.TimeoutError()

    with pytest.raises(asyncio.TimeoutError):
        await mcp_client.call_tool(session=mock_session, tool_name="echo", arguments={"message": "test"}, timeout=1.0)


@pytest.mark.asyncio
async def test_create_stdio_session_success(mcp_client, stdio_transport_config):
    """Test successful STDIO session creation."""
    mock_exit_stack = AsyncMock()
    mock_session = AsyncMock()

    with patch("catmandu.core.clients.mcp.AsyncExitStack", return_value=mock_exit_stack):
        with patch("catmandu.core.clients.mcp.stdio_client"):
            with patch("catmandu.core.clients.mcp.ClientSession", return_value=mock_session):
                mock_exit_stack.enter_async_context.side_effect = [
                    ("reader", "writer"),  # stdio_client result
                    mock_session,  # ClientSession result
                ]

                exit_stack, session = await mcp_client.create_session(stdio_transport_config)

                assert exit_stack == mock_exit_stack
                assert session == mock_session
                mock_session.initialize.assert_called_once()


@pytest.mark.asyncio
async def test_create_websocket_session_success(mcp_client, websocket_transport_config):
    """Test successful WebSocket session creation."""
    mock_exit_stack = AsyncMock()
    mock_session = AsyncMock()

    with patch("catmandu.core.clients.mcp.AsyncExitStack", return_value=mock_exit_stack):
        with patch("catmandu.core.clients.mcp.websocket_client"):
            with patch("catmandu.core.clients.mcp.ClientSession", return_value=mock_session):
                mock_exit_stack.enter_async_context.side_effect = [
                    ("reader", "writer"),  # websocket_client result
                    mock_session,  # ClientSession result
                ]

                exit_stack, session = await mcp_client.create_session(websocket_transport_config)

                assert exit_stack == mock_exit_stack
                assert session == mock_session
                mock_session.initialize.assert_called_once()


@pytest.mark.asyncio
async def test_create_http_session_success(mcp_client, http_transport_config):
    """Test successful HTTP session creation."""
    mock_exit_stack = AsyncMock()
    mock_session = AsyncMock()

    with patch("catmandu.core.clients.mcp.AsyncExitStack", return_value=mock_exit_stack):
        with patch("catmandu.core.clients.mcp.streamablehttp_client"):
            with patch("catmandu.core.clients.mcp.ClientSession", return_value=mock_session):
                mock_exit_stack.enter_async_context.side_effect = [
                    ("reader", "writer", "get_session_id"),  # streamablehttp_client result
                    mock_session,  # ClientSession result
                ]

                exit_stack, session = await mcp_client.create_session(http_transport_config)

                assert exit_stack == mock_exit_stack
                assert session == mock_session
                assert hasattr(session, "get_session_id")
                mock_session.initialize.assert_called_once()


@pytest.mark.asyncio
async def test_check_session_health_success(mcp_client):
    """Test successful session health check."""
    mock_session = AsyncMock()
    mock_session.list_tools.return_value = []

    result = await mcp_client.check_session_health(mock_session)

    assert result is True
    mock_session.list_tools.assert_called_once()


@pytest.mark.asyncio
async def test_check_session_health_failure(mcp_client):
    """Test failed session health check."""
    mock_session = AsyncMock()
    mock_session.list_tools.side_effect = Exception("Connection lost")

    result = await mcp_client.check_session_health(mock_session)

    assert result is False
    mock_session.list_tools.assert_called_once()


@pytest.mark.asyncio
async def test_unsupported_transport_type(mcp_client):
    """Test error handling for unsupported transport type."""
    unsupported_config = MagicMock()
    unsupported_config.type = "unsupported"

    with pytest.raises(CattackleExecutionError, match="Unsupported transport type"):
        await mcp_client.create_session(unsupported_config)
