import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp import ClientSession

from catmandu.core.errors import CattackleExecutionError
from catmandu.core.models import (
    CattackleConfig,
    CattackleDetails,
    CommandsConfig,
    HttpTransportConfig,
    McpConfig,
    StdioTransportConfig,
    WebSocketTransportConfig,
)
from catmandu.core.services.mcp_client import McpClientManager


@pytest.fixture
def stdio_cattackle_config():
    """Create a sample STDIO cattackle configuration for testing."""
    return CattackleConfig(
        cattackle=CattackleDetails(
            name="test-cattackle",
            version="0.1.0",
            description="Test cattackle",
            commands={
                "echo": CommandsConfig(description="Echo command"),
                "ping": CommandsConfig(description="Ping command"),
            },
            mcp=McpConfig(
                transport=StdioTransportConfig(
                    type="stdio",
                    command="python",
                    args=["-m", "test.server"],
                    env={"TEST": "true", "LOG_LEVEL": "INFO"},
                    cwd=".",
                ),
                timeout=10.0,
                max_retries=2,
            ),
        )
    )


@pytest.fixture
def websocket_cattackle_config():
    """Create a sample WebSocket cattackle configuration for testing."""
    return CattackleConfig(
        cattackle=CattackleDetails(
            name="ws-cattackle",
            version="0.1.0",
            description="WebSocket cattackle",
            commands={"echo": CommandsConfig(description="Echo command")},
            mcp=McpConfig(
                transport=WebSocketTransportConfig(
                    type="websocket",
                    url="ws://localhost:8080/mcp",
                    headers={"Authorization": "Bearer test-token"},
                ),
                timeout=10.0,
                max_retries=2,
            ),
        )
    )


@pytest.fixture
def http_cattackle_config():
    """Create a sample HTTP cattackle configuration for testing."""
    return CattackleConfig(
        cattackle=CattackleDetails(
            name="http-cattackle",
            version="0.1.0",
            description="HTTP cattackle",
            commands={"echo": CommandsConfig(description="Echo command")},
            mcp=McpConfig(
                transport=HttpTransportConfig(
                    type="http",
                    url="http://localhost:8080/mcp",
                    headers={"Authorization": "Bearer test-token"},
                ),
                timeout=10.0,
                max_retries=2,
            ),
        )
    )


@pytest.fixture
def mcp_client_manager():
    """Create an MCP client manager instance."""
    return McpClientManager()


@pytest.mark.asyncio
async def test_call_success(mcp_client_manager, stdio_cattackle_config):
    """Test successful cattackle call."""
    # Mock the session and response
    mock_session = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text={"result": "success", "metadata": {"timestamp": 1234567890}})]
    mock_session.call_tool.return_value = mock_response

    with patch.object(mcp_client_manager, "_get_or_create_session", return_value=mock_session):
        response = await mcp_client_manager.call(stdio_cattackle_config, "echo", {"message": "test"})

        assert "result" in response.data
        assert response.data["result"] == "success"
        assert "metadata" in response.data
        mock_session.call_tool.assert_called_once_with("echo", {"payload": {"message": "test"}})


@pytest.mark.asyncio
async def test_call_timeout(mcp_client_manager, stdio_cattackle_config):
    """Test cattackle call timeout with retry logic."""
    mock_session = AsyncMock()
    mock_session.call_tool.side_effect = asyncio.TimeoutError()

    with patch.object(mcp_client_manager, "_get_or_create_session", return_value=mock_session):
        with patch("asyncio.sleep", return_value=None):  # Skip waiting during retries
            with pytest.raises(CattackleExecutionError, match="timed out"):
                await mcp_client_manager.call(stdio_cattackle_config, "echo", {"message": "test"})

            # Should have tried max_retries + 1 times (initial + retries)
            assert mock_session.call_tool.call_count == stdio_cattackle_config.cattackle.mcp.max_retries + 1


@pytest.mark.asyncio
async def test_session_caching(mcp_client_manager, stdio_cattackle_config):
    """Test that sessions are cached and reused."""
    mock_session = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text={"result": "cached"})]
    mock_session.call_tool.return_value = mock_response

    with patch.object(mcp_client_manager, "_create_stdio_session", return_value=mock_session) as mock_create:
        with patch.object(mcp_client_manager, "_check_session_health", return_value=True):
            # First call should create session
            await mcp_client_manager.call(stdio_cattackle_config, "echo", {})
            assert mock_create.call_count == 1

            # Second call should reuse session
            await mcp_client_manager.call(stdio_cattackle_config, "echo", {})
            assert mock_create.call_count == 1  # Still only called once


@pytest.mark.asyncio
async def test_session_health_check(mcp_client_manager, stdio_cattackle_config):
    """Test session health check and recreation."""
    mock_session1 = AsyncMock()
    mock_session2 = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text={"result": "success"})]
    mock_session1.call_tool.return_value = mock_response
    mock_session2.call_tool.return_value = mock_response

    # First call with healthy session
    with patch.object(mcp_client_manager, "_create_stdio_session", return_value=mock_session1) as mock_create:
        with patch.object(mcp_client_manager, "_check_session_health", return_value=True):
            await mcp_client_manager.call(stdio_cattackle_config, "echo", {})
            assert mock_create.call_count == 1

    # Second call with unhealthy session should recreate
    with patch.object(mcp_client_manager, "_create_stdio_session", return_value=mock_session2) as mock_create:
        with patch.object(mcp_client_manager, "_check_session_health", return_value=False):
            await mcp_client_manager.call(stdio_cattackle_config, "echo", {})
            assert mock_create.call_count == 1  # Called again to create new session


@pytest.mark.asyncio
async def test_close_session(mcp_client_manager):
    """Test session cleanup."""
    mock_session = AsyncMock()
    mcp_client_manager._active_sessions["test"] = mock_session

    await mcp_client_manager.close_session("test")

    assert "test" not in mcp_client_manager._active_sessions
    mock_session.close.assert_called_once()


@pytest.mark.asyncio
async def test_close_all_sessions(mcp_client_manager):
    """Test closing all sessions."""
    mock_session1 = AsyncMock()
    mock_session2 = AsyncMock()
    mcp_client_manager._active_sessions = {
        "test1": mock_session1,
        "test2": mock_session2,
    }

    await mcp_client_manager.close_all_sessions()

    assert len(mcp_client_manager._active_sessions) == 0
    mock_session1.close.assert_called_once()
    mock_session2.close.assert_called_once()


@pytest.mark.asyncio
async def test_websocket_transport(mcp_client_manager, websocket_cattackle_config):
    """Test WebSocket transport creation."""
    # Test that we get a session back
    session = await mcp_client_manager._create_websocket_session(websocket_cattackle_config.cattackle.mcp.transport)

    # Verify it's a ClientSession instance
    assert isinstance(session, ClientSession)
    # Verify it has the expected methods
    assert hasattr(session, "initialize")
    assert hasattr(session, "call_tool")
    # Verify our added close method is present
    assert hasattr(session, "close")


@pytest.mark.asyncio
async def test_http_transport(mcp_client_manager, http_cattackle_config):
    """Test HTTP transport creation."""
    # Test that we get a session back
    session = await mcp_client_manager._create_http_session(http_cattackle_config.cattackle.mcp.transport)

    # Verify it's a ClientSession instance
    assert isinstance(session, ClientSession)
    # Verify it has the expected methods
    assert hasattr(session, "initialize")
    assert hasattr(session, "call_tool")
    # Verify our added close method is present
    assert hasattr(session, "close")
