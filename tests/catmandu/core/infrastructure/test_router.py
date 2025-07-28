"""Tests for MessageRouter."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from catmandu.core.infrastructure.mcp_manager import McpService
from catmandu.core.infrastructure.registry import CattackleRegistry
from catmandu.core.infrastructure.router import MessageRouter
from catmandu.core.models import CattackleConfig, CommandsConfig, McpConfig, StdioTransportConfig
from catmandu.core.services.accumulator import MessageAccumulator
from catmandu.core.services.accumulator_manager import AccumulatorManager


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
def accumulator_manager():
    """Create a real AccumulatorManager with feedback enabled for testing."""
    accumulator = MessageAccumulator(max_messages_per_chat=100, max_message_length=1000)
    return AccumulatorManager(accumulator, feedback_enabled=True)


@pytest.fixture
def router(mock_mcp_service, mock_registry, accumulator_manager):
    """Create a MessageRouter with mocked dependencies."""
    return MessageRouter(mock_mcp_service, mock_registry, accumulator_manager)


@pytest.mark.asyncio
async def test_process_update_cattackle_command_format(router, mock_mcp_service, mock_registry, accumulator_manager):
    """Test processing a command in cattackle_command format."""
    # Pre-populate accumulator with test data
    accumulator_manager.process_non_command_message(123, "param1")
    accumulator_manager.process_non_command_message(123, "param2")

    update = {"message": {"chat": {"id": 123}, "text": "/echo_echo test message"}}

    result = await router.process_update(update)

    assert result is not None
    chat_id, response = result
    assert chat_id == 123
    assert response == "{'result': 'test response'}"

    # Verify the registry was called with the correct parameters
    mock_registry.find_by_cattackle_and_command.assert_called_once_with("echo", "echo")

    # Verify accumulator was cleared after parameter extraction
    assert (
        accumulator_manager.get_accumulator_status(123)
        == "📭 No messages accumulated. Send some messages and then use a command!"
    )

    # Verify MCP service was called with simplified payload
    mock_mcp_service.execute_cattackle.assert_called_once()
    call_args = mock_mcp_service.execute_cattackle.call_args
    payload = call_args[1]["payload"]
    assert "accumulated_params" in payload
    assert payload["accumulated_params"] == ["param1", "param2"]
    assert "text" in payload
    assert payload["text"] == "test message"


@pytest.mark.asyncio
async def test_process_update_fallback_to_old_format(router, mock_mcp_service, mock_registry, accumulator_manager):
    """Test processing a command in old format (fallback behavior)."""
    # Pre-populate accumulator with test data
    accumulator_manager.process_non_command_message(123, "param1")
    accumulator_manager.process_non_command_message(123, "param2")

    update = {"message": {"chat": {"id": 123}, "text": "/ping test message"}}

    result = await router.process_update(update)

    assert result is not None
    chat_id, response = result
    assert chat_id == 123
    assert response == "{'result': 'test response'}"

    # Verify the registry was called with fallback method
    mock_registry.find_by_command.assert_called_once_with("ping")

    # Verify accumulator was cleared after parameter extraction
    assert (
        accumulator_manager.get_accumulator_status(123)
        == "📭 No messages accumulated. Send some messages and then use a command!"
    )

    # Verify MCP service was called with simplified payload
    mock_mcp_service.execute_cattackle.assert_called_once()
    call_args = mock_mcp_service.execute_cattackle.call_args
    payload = call_args[1]["payload"]
    assert "accumulated_params" in payload
    assert payload["accumulated_params"] == ["param1", "param2"]
    assert "text" in payload
    assert payload["text"] == "test message"


@pytest.mark.asyncio
async def test_process_update_command_not_found(router, mock_mcp_service, mock_registry, accumulator_manager):
    """Test processing a non-existent command."""
    # Pre-populate accumulator to verify it's not cleared on command not found
    accumulator_manager.process_non_command_message(123, "param1")
    initial_status = accumulator_manager.get_accumulator_status(123)

    update = {"message": {"chat": {"id": 123}, "text": "/nonexistent_command test message"}}

    result = await router.process_update(update)

    assert result is not None
    chat_id, response = result
    assert chat_id == 123
    assert response == "Command not found: nonexistent_command"

    # Verify the registry was called
    mock_registry.find_by_cattackle_and_command.assert_called_once_with("nonexistent", "command")

    # Verify accumulator was not cleared (since command wasn't found)
    assert accumulator_manager.get_accumulator_status(123) == initial_status

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
async def test_process_update_non_command_message(router, accumulator_manager):
    """Test processing a non-command message for accumulation."""
    update = {"message": {"chat": {"id": 123}, "text": "regular message"}}

    result = await router.process_update(update)

    assert result is not None
    chat_id, response = result
    assert chat_id == 123
    assert response == "📝 Message stored. You now have 1 message ready for your next command."

    # Verify message was stored in accumulator
    assert (
        accumulator_manager.get_accumulator_status(123)
        == "📝 You have 1 message accumulated and ready for your next command."
    )
    messages = accumulator_manager._accumulator.get_messages(123)
    assert messages == ["regular message"]


@pytest.mark.asyncio
async def test_process_update_non_command_message_no_feedback(mock_mcp_service, mock_registry):
    """Test processing a non-command message when feedback is disabled."""
    # Create accumulator manager with feedback disabled
    accumulator = MessageAccumulator(max_messages_per_chat=100, max_message_length=1000)
    accumulator_manager = AccumulatorManager(accumulator, feedback_enabled=False)
    router = MessageRouter(mock_mcp_service, mock_registry, accumulator_manager)

    update = {"message": {"chat": {"id": 123}, "text": "regular message"}}

    result = await router.process_update(update)

    assert result is None

    # Verify message was still stored in accumulator (just no feedback)
    assert (
        accumulator_manager.get_accumulator_status(123)
        == "📝 You have 1 message accumulated and ready for your next command."
    )
    messages = accumulator_manager._accumulator.get_messages(123)
    assert messages == ["regular message"]


@pytest.mark.asyncio
async def test_process_update_system_command_clear_accumulator(router, accumulator_manager):
    """Test processing /clear_accumulator system command."""
    # Pre-populate accumulator with test data
    accumulator_manager.process_non_command_message(123, "param1")
    accumulator_manager.process_non_command_message(123, "param2")

    update = {"message": {"chat": {"id": 123}, "text": "/clear_accumulator"}}

    result = await router.process_update(update)

    assert result is not None
    chat_id, response = result
    assert chat_id == 123
    assert response == "🗑️ Cleared 2 accumulated messages."

    # Verify accumulator was actually cleared
    assert (
        accumulator_manager.get_accumulator_status(123)
        == "📭 No messages accumulated. Send some messages and then use a command!"
    )


@pytest.mark.asyncio
async def test_process_update_system_command_show_accumulator(router, accumulator_manager):
    """Test processing /show_accumulator system command."""
    # Pre-populate accumulator with test data
    accumulator_manager.process_non_command_message(123, "param1")
    accumulator_manager.process_non_command_message(123, "param2")

    update = {"message": {"chat": {"id": 123}, "text": "/show_accumulator"}}

    result = await router.process_update(update)

    assert result is not None
    chat_id, response = result
    assert chat_id == 123
    assert response == "📝 Your accumulated messages (2 total):\n1. param1\n2. param2"

    # Verify accumulator still contains the messages (show doesn't clear)
    assert (
        accumulator_manager.get_accumulator_status(123)
        == "📝 You have 2 messages accumulated and ready for your next command."
    )


@pytest.mark.asyncio
async def test_process_update_system_command_accumulator_status(router, accumulator_manager):
    """Test processing /accumulator_status system command."""
    # Pre-populate accumulator with test data
    accumulator_manager.process_non_command_message(123, "param1")
    accumulator_manager.process_non_command_message(123, "param2")

    update = {"message": {"chat": {"id": 123}, "text": "/accumulator_status"}}

    result = await router.process_update(update)

    assert result is not None
    chat_id, response = result
    assert chat_id == 123
    assert response == "📝 You have 2 messages accumulated and ready for your next command."

    # Verify accumulator still contains the messages (status doesn't clear)
    messages = accumulator_manager._accumulator.get_messages(123)
    assert messages == ["param1", "param2"]


@pytest.mark.asyncio
async def test_process_command_with_accumulated_parameters(
    router, mock_mcp_service, mock_registry, accumulator_manager
):
    """Test that commands receive accumulated parameters in payload."""
    # Pre-populate accumulator with test data
    accumulator_manager.process_non_command_message(123, "param1")
    accumulator_manager.process_non_command_message(123, "param2")

    update = {"message": {"chat": {"id": 123}, "text": "/echo_echo"}}

    result = await router.process_update(update)

    assert result is not None
    chat_id, response = result
    assert chat_id == 123

    # Verify MCP service was called with simplified payload including accumulated_params
    mock_mcp_service.execute_cattackle.assert_called_once()
    call_args = mock_mcp_service.execute_cattackle.call_args
    payload = call_args[1]["payload"]

    # Check simplified payload structure
    assert "text" in payload
    assert "accumulated_params" in payload
    assert payload["accumulated_params"] == ["param1", "param2"]
    assert payload["text"] == ""  # No additional text after command

    # Verify accumulator was cleared after parameter extraction
    assert (
        accumulator_manager.get_accumulator_status(123)
        == "📭 No messages accumulated. Send some messages and then use a command!"
    )


@pytest.mark.asyncio
async def test_process_command_with_text_and_accumulated_parameters(
    router, mock_mcp_service, mock_registry, accumulator_manager
):
    """Test that commands receive both text and accumulated parameters in payload."""
    # Pre-populate accumulator with test data
    accumulator_manager.process_non_command_message(123, "param1")
    accumulator_manager.process_non_command_message(123, "param2")

    update = {"message": {"chat": {"id": 123}, "text": "/echo_echo immediate param"}}

    result = await router.process_update(update)

    assert result is not None

    # Verify MCP service was called with simplified payload
    mock_mcp_service.execute_cattackle.assert_called_once()
    call_args = mock_mcp_service.execute_cattackle.call_args
    payload = call_args[1]["payload"]

    # Check simplified payload structure
    assert payload["text"] == "immediate param"
    assert payload["accumulated_params"] == ["param1", "param2"]

    # Verify accumulator was cleared after parameter extraction
    assert (
        accumulator_manager.get_accumulator_status(123)
        == "📭 No messages accumulated. Send some messages and then use a command!"
    )


@pytest.mark.asyncio
async def test_process_command_clears_accumulator_after_extraction(
    router, mock_mcp_service, mock_registry, accumulator_manager
):
    """Test that accumulator is cleared after parameter extraction."""
    # Pre-populate accumulator with test data
    accumulator_manager.process_non_command_message(123, "param1")
    accumulator_manager.process_non_command_message(123, "param2")

    # Verify accumulator has messages before command
    assert (
        accumulator_manager.get_accumulator_status(123)
        == "📝 You have 2 messages accumulated and ready for your next command."
    )

    update = {"message": {"chat": {"id": 123}, "text": "/echo_echo"}}

    await router.process_update(update)

    # Verify accumulator was cleared after parameter extraction
    assert (
        accumulator_manager.get_accumulator_status(123)
        == "📭 No messages accumulated. Send some messages and then use a command!"
    )


@pytest.mark.asyncio
async def test_enhanced_routing_logic_both_message_types(router, accumulator_manager, mock_mcp_service, mock_registry):
    """Test that router handles both command and non-command messages correctly."""
    # First, send a non-command message
    non_command_update = {"message": {"chat": {"id": 123}, "text": "accumulated message"}}
    result1 = await router.process_update(non_command_update)

    assert result1 is not None
    chat_id1, response1 = result1
    assert chat_id1 == 123
    assert "Message stored" in response1

    # Verify message was accumulated
    assert (
        accumulator_manager.get_accumulator_status(123)
        == "📝 You have 1 message accumulated and ready for your next command."
    )

    # Then, send a command
    command_update = {"message": {"chat": {"id": 123}, "text": "/echo_echo"}}
    result2 = await router.process_update(command_update)

    assert result2 is not None
    chat_id2, response2 = result2
    assert chat_id2 == 123

    # Verify command was processed and accumulator was cleared
    assert (
        accumulator_manager.get_accumulator_status(123)
        == "📭 No messages accumulated. Send some messages and then use a command!"
    )
    mock_mcp_service.execute_cattackle.assert_called_once()

    # Verify the command received the accumulated message as parameter
    call_args = mock_mcp_service.execute_cattackle.call_args
    payload = call_args[1]["payload"]
    assert payload["accumulated_params"] == ["accumulated message"]
    # Verify simplified payload structure
    assert "text" in payload


@pytest.mark.asyncio
async def test_system_command_clear_accumulator_empty(router, accumulator_manager):
    """Test /clear_accumulator system command when accumulator is already empty."""
    update = {"message": {"chat": {"id": 123}, "text": "/clear_accumulator"}}

    result = await router.process_update(update)

    assert result is not None
    chat_id, response = result
    assert chat_id == 123
    assert response == "📭 No messages to clear - your accumulator is already empty."


@pytest.mark.asyncio
async def test_system_command_show_accumulator_empty(router, accumulator_manager):
    """Test /show_accumulator system command when accumulator is empty."""
    update = {"message": {"chat": {"id": 123}, "text": "/show_accumulator"}}

    result = await router.process_update(update)

    assert result is not None
    chat_id, response = result
    assert chat_id == 123
    assert response == "📭 No messages accumulated."


@pytest.mark.asyncio
async def test_system_command_accumulator_status_empty(router, accumulator_manager):
    """Test /accumulator_status system command when accumulator is empty."""
    update = {"message": {"chat": {"id": 123}, "text": "/accumulator_status"}}

    result = await router.process_update(update)

    assert result is not None
    chat_id, response = result
    assert chat_id == 123
    assert response == "📭 No messages accumulated. Send some messages and then use a command!"


@pytest.mark.asyncio
async def test_system_command_clear_accumulator_single_message(router, accumulator_manager):
    """Test /clear_accumulator system command with single message."""
    # Pre-populate accumulator with single message
    accumulator_manager.process_non_command_message(123, "single param")

    update = {"message": {"chat": {"id": 123}, "text": "/clear_accumulator"}}

    result = await router.process_update(update)

    assert result is not None
    chat_id, response = result
    assert chat_id == 123
    assert response == "🗑️ Cleared 1 accumulated message."

    # Verify accumulator was actually cleared
    assert (
        accumulator_manager.get_accumulator_status(123)
        == "📭 No messages accumulated. Send some messages and then use a command!"
    )


@pytest.mark.asyncio
async def test_system_command_show_accumulator_single_message(router, accumulator_manager):
    """Test /show_accumulator system command with single message."""
    # Pre-populate accumulator with single message
    accumulator_manager.process_non_command_message(123, "single param")

    update = {"message": {"chat": {"id": 123}, "text": "/show_accumulator"}}

    result = await router.process_update(update)

    assert result is not None
    chat_id, response = result
    assert chat_id == 123
    assert response == "📝 Your accumulated messages (1 total):\n1. single param"

    # Verify accumulator still contains the message (show doesn't clear)
    assert (
        accumulator_manager.get_accumulator_status(123)
        == "📝 You have 1 message accumulated and ready for your next command."
    )


@pytest.mark.asyncio
async def test_system_command_accumulator_status_single_message(router, accumulator_manager):
    """Test /accumulator_status system command with single message."""
    # Pre-populate accumulator with single message
    accumulator_manager.process_non_command_message(123, "single param")

    update = {"message": {"chat": {"id": 123}, "text": "/accumulator_status"}}

    result = await router.process_update(update)

    assert result is not None
    chat_id, response = result
    assert chat_id == 123
    assert response == "📝 You have 1 message accumulated and ready for your next command."

    # Verify accumulator still contains the message (status doesn't clear)
    messages = accumulator_manager._accumulator.get_messages(123)
    assert messages == ["single param"]


@pytest.mark.asyncio
async def test_system_command_show_accumulator_long_messages(router, accumulator_manager):
    """Test /show_accumulator system command with long messages that get truncated for display."""
    # Pre-populate accumulator with long message (over 100 characters)
    long_message = (
        "This is a very long message that should be truncated for display purposes "
        "when shown to the user because it exceeds the limit"
    )
    accumulator_manager.process_non_command_message(123, long_message)

    update = {"message": {"chat": {"id": 123}, "text": "/show_accumulator"}}

    result = await router.process_update(update)

    assert result is not None
    chat_id, response = result
    assert chat_id == 123
    # The message should be truncated to 100 characters for display
    expected_truncated = long_message[:100] + "..."
    assert response == f"📝 Your accumulated messages (1 total):\n1. {expected_truncated}"


@pytest.mark.asyncio
async def test_system_commands_chat_isolation(router, accumulator_manager):
    """Test that system commands work correctly with chat isolation."""
    # Pre-populate accumulator for two different chats
    accumulator_manager.process_non_command_message(123, "chat123 message")
    accumulator_manager.process_non_command_message(456, "chat456 message")

    # Test status for chat 123
    update_123 = {"message": {"chat": {"id": 123}, "text": "/accumulator_status"}}
    result_123 = await router.process_update(update_123)

    assert result_123 is not None
    chat_id_123, response_123 = result_123
    assert chat_id_123 == 123
    assert response_123 == "📝 You have 1 message accumulated and ready for your next command."

    # Test status for chat 456
    update_456 = {"message": {"chat": {"id": 456}, "text": "/accumulator_status"}}
    result_456 = await router.process_update(update_456)

    assert result_456 is not None
    chat_id_456, response_456 = result_456
    assert chat_id_456 == 456
    assert response_456 == "📝 You have 1 message accumulated and ready for your next command."

    # Clear accumulator for chat 123
    clear_update = {"message": {"chat": {"id": 123}, "text": "/clear_accumulator"}}
    await router.process_update(clear_update)

    # Verify chat 123 is cleared but chat 456 still has messages
    result_123_after = await router.process_update(update_123)
    assert result_123_after[1] == "📭 No messages accumulated. Send some messages and then use a command!"

    result_456_after = await router.process_update(update_456)
    assert result_456_after[1] == "📝 You have 1 message accumulated and ready for your next command."


@pytest.mark.asyncio
async def test_system_commands_do_not_route_to_mcp_service(router, mock_mcp_service, accumulator_manager):
    """Test that system commands are handled directly and not routed to MCP service."""
    # Pre-populate accumulator
    accumulator_manager.process_non_command_message(123, "test message")

    # Test all system commands
    system_commands = ["/clear_accumulator", "/show_accumulator", "/accumulator_status"]

    for command in system_commands:
        update = {"message": {"chat": {"id": 123}, "text": command}}
        result = await router.process_update(update)

        assert result is not None
        chat_id, response = result
        assert chat_id == 123
        assert response is not None

    # Verify MCP service was never called for system commands
    mock_mcp_service.execute_cattackle.assert_not_called()


@pytest.mark.asyncio
async def test_simplified_payload_structure_requirements(router, mock_mcp_service, mock_registry, accumulator_manager):
    """Test that payload structure meets simplified requirements - only text and accumulated_params fields."""
    # Pre-populate accumulator with test data
    accumulator_manager.process_non_command_message(123, "accumulated message")

    # Create a complex message object with many fields
    complex_message = {
        "chat": {"id": 123, "type": "private", "username": "testuser"},
        "text": "/echo_echo immediate text",
        "from": {"id": 456, "username": "sender", "first_name": "Test"},
        "message_id": 789,
        "date": 1234567890,
        "entities": [{"type": "bot_command", "offset": 0, "length": 10}],
    }
    update = {"message": complex_message}

    result = await router.process_update(update)

    assert result is not None
    mock_mcp_service.execute_cattackle.assert_called_once()
    call_args = mock_mcp_service.execute_cattackle.call_args
    payload = call_args[1]["payload"]

    # Verify payload contains ONLY the required fields
    assert len(payload) == 2, f"Payload should contain exactly 2 fields, got {len(payload)}: {list(payload.keys())}"
    assert "text" in payload, "Payload must contain 'text' field"
    assert "accumulated_params" in payload, "Payload must contain 'accumulated_params' field"

    # Verify the "message" field is NOT present

    # Verify field values are correct
    assert payload["text"] == "immediate text"
    assert payload["accumulated_params"] == ["accumulated message"]


@pytest.mark.asyncio
async def test_payload_format_simplified_structure(router, mock_mcp_service, mock_registry, accumulator_manager):
    """Test that payload format uses simplified structure with only text and accumulated_params fields."""
    # Test command without accumulated parameters (empty accumulator)
    update = {"message": {"chat": {"id": 123}, "text": "/echo_echo immediate text", "from": {"id": 456}}}

    result = await router.process_update(update)

    assert result is not None
    mock_mcp_service.execute_cattackle.assert_called_once()
    call_args = mock_mcp_service.execute_cattackle.call_args
    payload = call_args[1]["payload"]

    # Verify simplified payload structure - only text and accumulated_params
    assert "text" in payload
    assert payload["text"] == "immediate text"

    # Verify accumulated_params field is present but empty (no accumulated messages)
    assert "accumulated_params" in payload
    assert payload["accumulated_params"] == []

    # Verify payload only contains expected fields
    assert len(payload) == 2


@pytest.mark.asyncio
async def test_payload_format_with_accumulated_parameters_complete(
    router, mock_mcp_service, mock_registry, accumulator_manager
):
    """Test complete simplified payload format with both immediate text and accumulated parameters."""
    # Pre-populate accumulator with multiple messages
    accumulator_manager.process_non_command_message(123, "first accumulated")
    accumulator_manager.process_non_command_message(123, "second accumulated")
    accumulator_manager.process_non_command_message(123, "third accumulated")

    # Send command with immediate text
    message_obj = {
        "chat": {"id": 123, "type": "private"},
        "text": "/echo_echo immediate parameter",
        "from": {"id": 456, "username": "testuser"},
        "message_id": 789,
    }
    update = {"message": message_obj}

    result = await router.process_update(update)

    assert result is not None
    mock_mcp_service.execute_cattackle.assert_called_once()
    call_args = mock_mcp_service.execute_cattackle.call_args
    payload = call_args[1]["payload"]

    # Verify simplified payload structure
    assert len(payload) == 2  # Only text and accumulated_params
    assert payload["text"] == "immediate parameter"
    assert payload["accumulated_params"] == ["first accumulated", "second accumulated", "third accumulated"]

    # Verify accumulator was cleared after extraction
    assert accumulator_manager._accumulator.get_messages(123) == []


@pytest.mark.asyncio
async def test_payload_format_empty_text_with_accumulated_parameters(
    router, mock_mcp_service, mock_registry, accumulator_manager
):
    """Test simplified payload format when command has no immediate text but has accumulated parameters."""
    # Pre-populate accumulator
    accumulator_manager.process_non_command_message(123, "only accumulated param")

    # Send command without immediate text
    update = {"message": {"chat": {"id": 123}, "text": "/echo_echo"}}

    result = await router.process_update(update)

    assert result is not None
    mock_mcp_service.execute_cattackle.assert_called_once()
    call_args = mock_mcp_service.execute_cattackle.call_args
    payload = call_args[1]["payload"]

    # Verify simplified payload structure
    assert payload["text"] == ""  # Empty string when no immediate text
    assert payload["accumulated_params"] == ["only accumulated param"]
    assert len(payload) == 2  # Only text and accumulated_params


@pytest.mark.asyncio
async def test_accumulator_cleared_after_parameter_extraction_regardless_of_execution_result(
    router, mock_mcp_service, mock_registry, accumulator_manager
):
    """Test that accumulator is always cleared after parameter extraction, even if command execution fails."""
    # Pre-populate accumulator
    accumulator_manager.process_non_command_message(123, "param1")
    accumulator_manager.process_non_command_message(123, "param2")

    # Mock MCP service to raise an exception
    from catmandu.core.errors import CattackleExecutionError

    mock_mcp_service.execute_cattackle.side_effect = CattackleExecutionError("Test error")

    update = {"message": {"chat": {"id": 123}, "text": "/echo_echo"}}

    result = await router.process_update(update)

    # Command should return error message
    assert result is not None
    chat_id, response = result
    assert chat_id == 123
    assert response == "An error occurred while executing the command."

    # Verify accumulator was still cleared despite the error
    assert accumulator_manager._accumulator.get_messages(123) == []
    assert (
        accumulator_manager.get_accumulator_status(123)
        == "📭 No messages accumulated. Send some messages and then use a command!"
    )
