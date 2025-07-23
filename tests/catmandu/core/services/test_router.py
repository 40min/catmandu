"""Tests for MessageRouter."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from catmandu.core.models import CattackleConfig, CommandsConfig, McpConfig, StdioTransportConfig
from catmandu.core.services.mcp_service import McpService
from catmandu.core.services.registry import CattackleRegistry
from catmandu.core.services.router import MessageRouter


@pytest.fixture
def mock_mcp_service():
    """Create a mock MCP service."""
    service = AsyncMock(spec=McpService)
    mock_response = MagicMock()
    mock_response.data = {"result": "test response"}
    service.execute_cattackle.return_value = mock_response
    return service


@pytest.fixture
def mock_registry():
    """Create a mock registry with test cattackles."""
    registry = MagicMock(spec=CattackleRegistry)

    # Create test cattackle configs
    echo_config = CattackleConfig(
        name="echo",
        version="0.1.0",
        description="Echo cattackle",
        commands={"echo": CommandsConfig(description="Echo command")},
        mcp=McpConfig(
            transport=StdioTransportConfig(type="stdio", command="python"),
            timeout=30.0,
            max_retries=3,
        ),
    )

    test_config = CattackleConfig(
        name="test",
        version="0.1.0",
        description="Test cattackle",
        commands={"ping": CommandsConfig(description="Ping command")},
        mcp=McpConfig(
            transport=StdioTransportConfig(type="stdio", command="python"),
            timeout=30.0,
            max_retries=3,
        ),
    )

    # Configure mock methods
    def find_by_cattackle_and_command(cattackle_name, command):
        if cattackle_name == "echo" and command == "echo":
            return echo_config
        elif cattackle_name == "test" and command == "ping":
            return test_config
        return None

    def find_by_command(command):
        if command == "echo":
            return echo_config
        elif command == "ping":
            return test_config
        return None

    registry.find_by_cattackle_and_command.side_effect = find_by_cattackle_and_command
    registry.find_by_command.side_effect = find_by_command

    return registry


@pytest.fixture
def router(mock_mcp_service, mock_registry):
    """Create a MessageRouter with mocked dependencies."""
    return MessageRouter(mock_mcp_service, mock_registry)


@pytest.mark.asyncio
async def test_process_update_cattackle_command_format(router, mock_mcp_service, mock_registry):
    """Test processing a command in cattackle_command format."""
    update = {"message": {"chat": {"id": 123}, "text": "/echo_echo test message"}}

    result = await router.process_update(update)

    assert result is not None
    chat_id, response = result
    assert chat_id == 123
    assert response == "{'result': 'test response'}"

    # Verify the registry was called with the correct parameters
    mock_registry.find_by_cattackle_and_command.assert_called_once_with("echo", "echo")

    # Verify MCP service was called
    mock_mcp_service.execute_cattackle.assert_called_once()


@pytest.mark.asyncio
async def test_process_update_fallback_to_old_format(router, mock_mcp_service, mock_registry):
    """Test processing a command in old format (fallback behavior)."""
    update = {"message": {"chat": {"id": 123}, "text": "/ping test message"}}

    result = await router.process_update(update)

    assert result is not None
    chat_id, response = result
    assert chat_id == 123
    assert response == "{'result': 'test response'}"

    # Verify the registry was called with fallback method
    mock_registry.find_by_command.assert_called_once_with("ping")

    # Verify MCP service was called
    mock_mcp_service.execute_cattackle.assert_called_once()


@pytest.mark.asyncio
async def test_process_update_command_not_found(router, mock_mcp_service, mock_registry):
    """Test processing a non-existent command."""
    update = {"message": {"chat": {"id": 123}, "text": "/nonexistent_command test message"}}

    result = await router.process_update(update)

    assert result is not None
    chat_id, response = result
    assert chat_id == 123
    assert response == "Command not found: nonexistent_command"

    # Verify the registry was called
    mock_registry.find_by_cattackle_and_command.assert_called_once_with("nonexistent", "command")

    # Verify MCP service was not called
    mock_mcp_service.execute_cattackle.assert_not_called()


@pytest.mark.asyncio
async def test_process_update_no_message(router):
    """Test processing an update without a message."""
    update = {"not_message": "something"}

    result = await router.process_update(update)

    assert result is None


@pytest.mark.asyncio
async def test_process_update_no_text(router):
    """Test processing a message without text."""
    update = {"message": {"chat": {"id": 123}, "not_text": "something"}}

    result = await router.process_update(update)

    assert result is None


@pytest.mark.asyncio
async def test_process_update_not_command(router):
    """Test processing a message that doesn't start with /."""
    update = {"message": {"chat": {"id": 123}, "text": "regular message"}}

    result = await router.process_update(update)

    assert result is None
