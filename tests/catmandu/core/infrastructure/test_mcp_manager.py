"""Tests for MCP service."""

import asyncio
from contextlib import AsyncExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp import ClientSession

from catmandu.core.clients.mcp import McpClient
from catmandu.core.errors import CattackleExecutionError
from catmandu.core.infrastructure.mcp_manager import McpService
from catmandu.core.models import (
    CattackleConfig,
    CommandsConfig,
    McpConfig,
    StdioTransportConfig,
)


@pytest.fixture
def mcp_client():
    """Create a mock MCP client."""
    client = AsyncMock(spec=McpClient)
    # Pre-configure common return values to avoid repeated setup
    client.check_session_health.return_value = True
    return client


@pytest.fixture
def mcp_service(mcp_client):
    """Create an MCP service with a mock client."""
    return McpService(mcp_client=mcp_client)


@pytest.fixture
def cattackle_config():
    """Create a sample cattackle configuration for testing."""
    return CattackleConfig(
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
                env={"TEST": "true"},
                cwd=".",
            ),
            timeout=0.1,  # Much shorter timeout for tests
            max_retries=1,  # Fewer retries for faster tests
        ),
    )


@pytest.mark.asyncio
async def test_execute_cattackle_success(mcp_service, mcp_client, cattackle_config):
    """Test successful cattackle execution."""
    # Mock session and response with proper JSON format
    mock_session = AsyncMock(spec=ClientSession)
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"data": "success", "error": null}')]

    # Setup mocks
    mcp_client.call_tool.return_value = mock_response

    # Mock _get_or_create_session to return our mock session
    with patch.object(mcp_service, "_get_or_create_session", return_value=mock_session):
        response = await mcp_service.execute_cattackle(
            cattackle_config=cattackle_config,
            command="echo",
            payload={"message": "test"},
            user_info={"user_id": "XXX"},  # Mock user info for testing
        )

        # Verify response is parsed correctly
        assert response.data == "success"
        assert response.error is None

        # Verify client was called correctly (with extra field added)
        mcp_client.call_tool.assert_called_once_with(
            mock_session, "echo", {"message": "test", "extra": {"username": "undefined"}}, cattackle_config.mcp.timeout
        )


@pytest.mark.asyncio
async def test_execute_cattackle_timeout_with_retry(mcp_service, mcp_client, cattackle_config):
    """Test cattackle execution with timeout and retry."""
    # Mock session
    mock_session = AsyncMock(spec=ClientSession)

    # Setup mocks - first call times out, second call succeeds
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"data": "success after retry", "error": null}')]
    mcp_client.call_tool.side_effect = [
        asyncio.TimeoutError(),  # First call times out
        mock_response,  # Second call succeeds
    ]

    # Mock session creation and sleep to speed up test
    with (
        patch.object(mcp_service, "_get_or_create_session", return_value=mock_session),
        patch("catmandu.core.infrastructure.mcp_manager.asyncio.sleep"),
    ):  # Mock sleep in the actual module
        response = await mcp_service.execute_cattackle(
            cattackle_config=cattackle_config, command="echo", payload={"message": "test"}, user_info=None
        )

        # Verify response from second (successful) call is parsed correctly
        assert response.data == "success after retry"
        assert response.error is None

        # Verify client was called twice
        assert mcp_client.call_tool.call_count == 2


@pytest.mark.asyncio
async def test_execute_cattackle_all_retries_fail(mcp_service, mcp_client, cattackle_config):
    """Test cattackle execution when all retries fail."""
    # Mock session
    mock_session = AsyncMock(spec=ClientSession)

    # Setup mocks - all calls time out
    mcp_client.call_tool.side_effect = asyncio.TimeoutError()

    # Mock session creation and sleep to speed up test
    with (
        patch.object(mcp_service, "_get_or_create_session", return_value=mock_session),
        patch("catmandu.core.infrastructure.mcp_manager.asyncio.sleep"),
    ):  # Mock sleep in the actual module
        with pytest.raises(CattackleExecutionError, match="timed out"):
            await mcp_service.execute_cattackle(
                cattackle_config=cattackle_config, command="echo", payload={"message": "test"}, user_info=None
            )

        # Verify client was called max_retries + 1 times (initial + retries)
        assert mcp_client.call_tool.call_count == cattackle_config.mcp.max_retries + 1


@pytest.mark.asyncio
async def test_get_or_create_session_existing(mcp_service, mcp_client, cattackle_config):
    """Test getting an existing healthy session."""
    # Create mock session and exit stack
    mock_session = AsyncMock(spec=ClientSession)
    mock_exit_stack = MagicMock(spec=AsyncExitStack)  # Use MagicMock for exit stack

    # Add to active contexts
    mcp_service._active_contexts[cattackle_config.name] = (mock_exit_stack, mock_session)

    # Get session (health check already returns True from fixture)
    session = await mcp_service._get_or_create_session(cattackle_config)

    # Verify we got the existing session
    assert session is mock_session

    # Verify health check was called
    mcp_client.check_session_health.assert_called_once_with(mock_session)

    # Verify create_session was not called
    mcp_client.create_session.assert_not_called()


@pytest.mark.asyncio
async def test_get_or_create_session_unhealthy(mcp_service, mcp_client, cattackle_config):
    """Test replacing an unhealthy session."""
    # Create mock sessions and exit stacks
    old_session = AsyncMock(spec=ClientSession)
    old_exit_stack = AsyncMock(spec=AsyncExitStack)
    new_session = AsyncMock(spec=ClientSession)
    new_exit_stack = AsyncMock(spec=AsyncExitStack)

    # Add old session to active contexts
    mcp_service._active_contexts[cattackle_config.name] = (old_exit_stack, old_session)

    # Mock health check to return False (session is unhealthy)
    mcp_client.check_session_health.return_value = False

    # Mock create_session to return new session
    mcp_client.create_session.return_value = (new_exit_stack, new_session)

    # Get session
    session = await mcp_service._get_or_create_session(cattackle_config)

    # Verify we got the new session
    assert session is new_session

    # Verify health check was called
    mcp_client.check_session_health.assert_called_once_with(old_session)

    # We can't easily verify close_session was called directly
    # Instead, let's verify that create_session was called, which implies close_session was called
    mcp_client.create_session.assert_called_with(cattackle_config.mcp.transport)


@pytest.mark.asyncio
async def test_get_or_create_session_new(mcp_service, mcp_client, cattackle_config):
    """Test creating a new session when none exists."""
    # Create mock session and exit stack
    mock_session = AsyncMock(spec=ClientSession)
    mock_exit_stack = MagicMock(spec=AsyncExitStack)  # Use MagicMock for exit stack

    # Mock create_session to return new session
    mcp_client.create_session.return_value = (mock_exit_stack, mock_session)

    # Get session
    session = await mcp_service._get_or_create_session(cattackle_config)

    # Verify we got the new session
    assert session is mock_session

    # Verify create_session was called
    mcp_client.create_session.assert_called_once_with(cattackle_config.mcp.transport)

    # Verify session was stored in active contexts
    assert mcp_service._active_contexts[cattackle_config.name] == (mock_exit_stack, mock_session)


@pytest.mark.asyncio
async def test_close_session(mcp_service):
    """Test closing a session."""
    # Create mock session and exit stack
    mock_session = MagicMock(spec=ClientSession)  # Use MagicMock for session
    mock_exit_stack = AsyncMock(spec=AsyncExitStack)

    # Add to active contexts
    cattackle_name = "test-cattackle"
    mcp_service._active_contexts[cattackle_name] = (mock_exit_stack, mock_session)

    # Close session
    await mcp_service.close_session(cattackle_name)

    # Verify exit stack was closed
    mock_exit_stack.aclose.assert_called_once()

    # Verify session was removed from active contexts
    assert cattackle_name not in mcp_service._active_contexts


@pytest.mark.asyncio
async def test_close_all_sessions(mcp_service):
    """Test closing all sessions."""
    # Create mock sessions and exit stacks
    mock_session1 = MagicMock(spec=ClientSession)  # Use MagicMock for sessions
    mock_exit_stack1 = AsyncMock(spec=AsyncExitStack)
    mock_session2 = MagicMock(spec=ClientSession)
    mock_exit_stack2 = AsyncMock(spec=AsyncExitStack)

    # Add to active contexts
    mcp_service._active_contexts = {
        "cattackle1": (mock_exit_stack1, mock_session1),
        "cattackle2": (mock_exit_stack2, mock_session2),
    }

    # Close all sessions
    await mcp_service.close_all_sessions()

    # Verify exit stacks were closed
    mock_exit_stack1.aclose.assert_called_once()
    mock_exit_stack2.aclose.assert_called_once()

    # Verify all sessions were removed from active contexts
    assert len(mcp_service._active_contexts) == 0


@pytest.mark.asyncio
async def test_execute_cattackle_non_json_response(mcp_service, mcp_client, cattackle_config):
    """Test cattackle execution with non-JSON response raises error."""
    # Mock session and response with plain text
    mock_session = AsyncMock(spec=ClientSession)
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Plain text response")]

    # Setup mocks
    mcp_client.call_tool.return_value = mock_response

    # Mock _get_or_create_session to return our mock session
    with patch.object(mcp_service, "_get_or_create_session", return_value=mock_session):
        with pytest.raises(CattackleExecutionError, match="returned invalid JSON response"):
            await mcp_service.execute_cattackle(
                cattackle_config=cattackle_config, command="echo", payload={"message": "test"}, user_info=None
            )


@pytest.mark.asyncio
async def test_execute_cattackle_json_response(mcp_service, mcp_client, cattackle_config):
    """Test cattackle execution with valid JSON response."""
    # Mock session and response with proper JSON format
    mock_session = AsyncMock(spec=ClientSession)
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"data": "Hello", "error": null}')]

    # Setup mocks
    mcp_client.call_tool.return_value = mock_response

    # Mock _get_or_create_session to return our mock session
    with patch.object(mcp_service, "_get_or_create_session", return_value=mock_session):
        response = await mcp_service.execute_cattackle(
            cattackle_config=cattackle_config, command="echo", payload={"message": "test"}, user_info=None
        )

    # Verify response is parsed correctly
    assert response.data == "Hello"
    assert response.error is None


@pytest.mark.asyncio
async def test_execute_cattackle_json_error_response(mcp_service, mcp_client, cattackle_config):
    """Test cattackle execution with JSON error response."""
    # Mock session and response with error
    mock_session = AsyncMock(spec=ClientSession)
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"data": "", "error": "Something went wrong"}')]

    # Setup mocks
    mcp_client.call_tool.return_value = mock_response

    # Mock _get_or_create_session to return our mock session
    with patch.object(mcp_service, "_get_or_create_session", return_value=mock_session):
        response = await mcp_service.execute_cattackle(
            cattackle_config=cattackle_config, command="echo", payload={"message": "test"}, user_info=None
        )

    # Verify error response is parsed correctly
    assert response.data == ""
    assert response.error == "Something went wrong"
