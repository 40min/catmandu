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
    mock_exit_stack = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text={"result": "cached"})]
    mock_session.call_tool.return_value = mock_response

    with patch.object(
        mcp_client_manager, "_create_stdio_session", return_value=(mock_exit_stack, mock_session)
    ) as mock_create:
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
    mock_exit_stack1 = AsyncMock()
    mock_exit_stack2 = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text={"result": "success"})]
    mock_session1.call_tool.return_value = mock_response
    mock_session2.call_tool.return_value = mock_response

    # First call with healthy session
    with patch.object(
        mcp_client_manager, "_create_stdio_session", return_value=(mock_exit_stack1, mock_session1)
    ) as mock_create:
        with patch.object(mcp_client_manager, "_check_session_health", return_value=True):
            await mcp_client_manager.call(stdio_cattackle_config, "echo", {})
            assert mock_create.call_count == 1

    # Second call with unhealthy session should recreate
    with patch.object(
        mcp_client_manager, "_create_stdio_session", return_value=(mock_exit_stack2, mock_session2)
    ) as mock_create:
        with patch.object(mcp_client_manager, "_check_session_health", return_value=False):
            await mcp_client_manager.call(stdio_cattackle_config, "echo", {})
            assert mock_create.call_count == 1  # Called again to create new session


@pytest.mark.asyncio
async def test_close_session(mcp_client_manager):
    """Test session cleanup."""
    mock_session = AsyncMock()
    mock_exit_stack = AsyncMock()
    mcp_client_manager._active_contexts["test"] = (mock_exit_stack, mock_session)

    await mcp_client_manager.close_session("test")

    assert "test" not in mcp_client_manager._active_contexts
    mock_exit_stack.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_close_all_sessions(mcp_client_manager):
    """Test closing all sessions."""
    mock_session1 = AsyncMock()
    mock_session2 = AsyncMock()
    mock_exit_stack1 = AsyncMock()
    mock_exit_stack2 = AsyncMock()
    mcp_client_manager._active_contexts = {
        "test1": (mock_exit_stack1, mock_session1),
        "test2": (mock_exit_stack2, mock_session2),
    }

    await mcp_client_manager.close_all_sessions()

    assert len(mcp_client_manager._active_contexts) == 0
    mock_exit_stack1.aclose.assert_called_once()
    mock_exit_stack2.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_get_or_create_session_by_transport_type(
    mcp_client_manager, stdio_cattackle_config, websocket_cattackle_config, http_cattackle_config
):
    """Test session creation based on transport type."""
    # Mock the session creation methods
    mock_stdio_session = AsyncMock()
    mock_websocket_session = AsyncMock()
    mock_http_session = AsyncMock()
    mock_exit_stack1 = AsyncMock()
    mock_exit_stack2 = AsyncMock()
    mock_exit_stack3 = AsyncMock()

    with patch.object(
        mcp_client_manager, "_create_stdio_session", return_value=(mock_exit_stack1, mock_stdio_session)
    ) as mock_create_stdio:
        with patch.object(
            mcp_client_manager, "_create_websocket_session", return_value=(mock_exit_stack2, mock_websocket_session)
        ) as mock_create_websocket:
            with patch.object(
                mcp_client_manager, "_create_http_session", return_value=(mock_exit_stack3, mock_http_session)
            ) as mock_create_http:
                # Test STDIO transport
                session = await mcp_client_manager._get_or_create_session(stdio_cattackle_config)
                assert session == mock_stdio_session
                mock_create_stdio.assert_called_once()

                # Test WebSocket transport
                session = await mcp_client_manager._get_or_create_session(websocket_cattackle_config)
                assert session == mock_websocket_session
                mock_create_websocket.assert_called_once()

                # Test HTTP transport
                session = await mcp_client_manager._get_or_create_session(http_cattackle_config)
                assert session == mock_http_session
                mock_create_http.assert_called_once()


@pytest.mark.asyncio
async def test_get_or_create_session_unsupported_transport(mcp_client_manager, stdio_cattackle_config):
    """Test error handling for unsupported transport types."""
    # Create a mock unsupported transport by patching isinstance checks
    from unittest.mock import MagicMock

    # Create a mock transport that doesn't match any of the supported types
    mock_transport = MagicMock()
    mock_transport.type = "unsupported"

    # Patch the transport in the config
    with patch.object(stdio_cattackle_config.cattackle.mcp, "transport", mock_transport):
        # Mock isinstance to return False for all supported transport types
        with patch("catmandu.core.services.mcp_client.isinstance", return_value=False):
            # Verify exception is raised for unsupported transport
            with pytest.raises(CattackleExecutionError, match="Unsupported transport type"):
                await mcp_client_manager._get_or_create_session(stdio_cattackle_config)


@pytest.mark.asyncio
async def test_websocket_transport(mcp_client_manager, websocket_cattackle_config):
    """Test WebSocket transport creation."""
    # Mock the websocket_client function as an async context manager
    mock_reader = AsyncMock()
    mock_writer = AsyncMock()
    mock_session = AsyncMock(spec=ClientSession)
    mock_session.initialize = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    # Create a mock async context manager for websocket_client
    mock_ws_context_manager = AsyncMock()
    mock_ws_context_manager.__aenter__ = AsyncMock(return_value=(mock_reader, mock_writer))
    mock_ws_context_manager.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "catmandu.core.services.mcp_client.websocket_client", return_value=mock_ws_context_manager
    ) as mock_ws_client:
        with patch("catmandu.core.services.mcp_client.ClientSession", return_value=mock_session):
            # Call the method
            exit_stack, session = await mcp_client_manager._create_websocket_session(
                websocket_cattackle_config.cattackle.mcp.transport
            )

            # Verify websocket_client was called with correct parameters
            mock_ws_client.assert_called_once_with(websocket_cattackle_config.cattackle.mcp.transport.url)

            # Verify session was initialized
            mock_session.initialize.assert_called_once()

            # Verify we got the session back
            assert session == mock_session
            # Verify we got an exit stack
            assert exit_stack is not None


@pytest.mark.asyncio
async def test_websocket_transport_error(mcp_client_manager, websocket_cattackle_config):
    """Test WebSocket transport creation error handling."""
    # Mock the websocket_client function to raise an exception
    with patch("catmandu.core.services.mcp_client.websocket_client", side_effect=Exception("Connection failed")):
        # Verify exception is properly wrapped
        with pytest.raises(CattackleExecutionError, match="Failed to create WebSocket session"):
            await mcp_client_manager._create_websocket_session(websocket_cattackle_config.cattackle.mcp.transport)


@pytest.mark.asyncio
async def test_http_transport(mcp_client_manager, http_cattackle_config):
    """Test HTTP transport creation."""
    # Mock the streamablehttp_client function as an async context manager
    mock_reader = AsyncMock()
    mock_writer = AsyncMock()
    mock_get_session_id = MagicMock(return_value="test-session-id")
    mock_session = AsyncMock(spec=ClientSession)
    mock_session.initialize = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    # Create a mock async context manager for streamablehttp_client
    mock_http_context_manager = AsyncMock()
    mock_http_context_manager.__aenter__ = AsyncMock(return_value=(mock_reader, mock_writer, mock_get_session_id))
    mock_http_context_manager.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "catmandu.core.services.mcp_client.streamablehttp_client", return_value=mock_http_context_manager
    ) as mock_http_client:
        with patch("catmandu.core.services.mcp_client.ClientSession", return_value=mock_session):
            # Call the method
            exit_stack, session = await mcp_client_manager._create_http_session(
                http_cattackle_config.cattackle.mcp.transport
            )

            # Verify streamablehttp_client was called with correct parameters
            mock_http_client.assert_called_once_with(
                http_cattackle_config.cattackle.mcp.transport.url,
                headers=http_cattackle_config.cattackle.mcp.transport.headers,
            )

            # Verify session was initialized
            mock_session.initialize.assert_called_once()

            # Verify get_session_id was attached
            assert hasattr(session, "get_session_id")
            assert session.get_session_id == mock_get_session_id

            # Verify we got the session back
            assert session == mock_session
            # Verify we got an exit stack
            assert exit_stack is not None


@pytest.mark.asyncio
async def test_http_transport_error(mcp_client_manager, http_cattackle_config):
    """Test HTTP transport creation error handling."""
    # Mock the streamablehttp_client function to raise an exception
    with patch("catmandu.core.services.mcp_client.streamablehttp_client", side_effect=Exception("Connection failed")):
        # Verify exception is properly wrapped
        with pytest.raises(CattackleExecutionError, match="Failed to create HTTP session"):
            await mcp_client_manager._create_http_session(http_cattackle_config.cattackle.mcp.transport)
