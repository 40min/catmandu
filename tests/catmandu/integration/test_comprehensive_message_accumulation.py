"""Comprehensive integration tests for message accumulation feature.

This module contains end-to-end integration tests that verify the complete
message accumulation workflow from Telegram updates through to cattackle execution.
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from catmandu.core.config import Settings
from catmandu.core.models import CattackleResponse
from catmandu.core.services.accumulator import MessageAccumulator
from catmandu.core.services.accumulator_manager import AccumulatorManager
from catmandu.core.services.poller import TelegramPoller
from catmandu.core.services.router import MessageRouter

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_telegram_client():
    """Create a mock TelegramClient for integration testing."""
    client = AsyncMock()
    return client


@pytest.fixture
def mock_mcp_service():
    """Create a mock McpService for integration testing."""
    service = AsyncMock()
    service.execute_cattackle.return_value = CattackleResponse(data="Echo: test response")
    return service


@pytest.fixture
def real_accumulator_manager():
    """Create a real AccumulatorManager with real MessageAccumulator for integration testing."""
    accumulator = MessageAccumulator(max_messages_per_chat=100, max_message_length=1000)
    return AccumulatorManager(accumulator, feedback_enabled=True)


@pytest.fixture
def temp_settings():
    """Create settings with a temporary file for offset storage."""
    with tempfile.TemporaryDirectory() as temp_dir:
        settings = Settings()
        settings.update_id_file_path = str(Path(temp_dir) / "update_id.txt")
        yield settings


@pytest.fixture
def integration_system(
    mock_telegram_client,
    mock_mcp_service,
    test_registry_with_cattackles,
    real_accumulator_manager,
    temp_settings,
):
    """Create a complete integrated system for testing."""
    message_router = MessageRouter(
        mcp_service=mock_mcp_service,
        cattackle_registry=test_registry_with_cattackles,
        accumulator_manager=real_accumulator_manager,
    )

    poller = TelegramPoller(
        router=message_router,
        telegram_client=mock_telegram_client,
        settings=temp_settings,
    )

    return {
        "poller": poller,
        "router": message_router,
        "accumulator_manager": real_accumulator_manager,
        "telegram_client": mock_telegram_client,
        "mcp_service": mock_mcp_service,
        "registry": test_registry_with_cattackles,
    }


class TestEndToEndMessageAccumulationFlow:
    """Test complete end-to-end message accumulation and command execution flows."""

    async def test_complete_accumulation_to_command_execution_flow(self, integration_system):
        """Test the complete flow: accumulate messages → execute command → clear accumulator."""
        system = integration_system
        chat_id = 12345

        # Phase 1: Accumulate multiple messages
        accumulation_updates = [
            {
                "update_id": 100,
                "message": {
                    "message_id": 200,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "First parameter",
                },
            },
            {
                "update_id": 101,
                "message": {
                    "message_id": 201,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "Second parameter",
                },
            },
            {
                "update_id": 102,
                "message": {
                    "message_id": 202,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "Third parameter",
                },
            },
        ]

        system["telegram_client"].get_updates.return_value = accumulation_updates
        await system["poller"]._run_single_loop()

        # Verify messages were accumulated
        accumulated = system["accumulator_manager"]._accumulator.get_messages(chat_id)
        assert len(accumulated) == 3
        assert accumulated == ["First parameter", "Second parameter", "Third parameter"]

        # Verify feedback was sent for each message
        assert system["telegram_client"].send_message.call_count == 3

        # Phase 2: Execute command with accumulated parameters
        command_updates = [
            {
                "update_id": 103,
                "message": {
                    "message_id": 203,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "/echo Additional command text",
                },
            }
        ]

        system["telegram_client"].get_updates.return_value = command_updates
        await system["poller"]._run_single_loop()

        # Verify command was executed with accumulated parameters
        system["mcp_service"].execute_cattackle.assert_called_once()
        call_args = system["mcp_service"].execute_cattackle.call_args

        assert call_args.kwargs["command"] == "echo"
        payload = call_args.kwargs["payload"]
        assert payload["text"] == "Additional command text"
        assert payload["accumulated_params"] == ["First parameter", "Second parameter", "Third parameter"]
        assert "message" in payload

        # Verify accumulator was cleared after command execution
        remaining = system["accumulator_manager"]._accumulator.get_messages(chat_id)
        assert len(remaining) == 0

        # Verify command response was sent
        system["telegram_client"].send_message.assert_called_with(chat_id, "Echo: test response")

    async def test_command_execution_without_accumulated_parameters(self, integration_system):
        """Test that commands work normally when no parameters are accumulated."""
        system = integration_system
        chat_id = 12345

        # Execute command without any accumulated messages
        command_updates = [
            {
                "update_id": 104,
                "message": {
                    "message_id": 204,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "/echo Direct command text",
                },
            }
        ]

        system["telegram_client"].get_updates.return_value = command_updates
        await system["poller"]._run_single_loop()

        # Verify command was executed with empty accumulated parameters
        system["mcp_service"].execute_cattackle.assert_called_once()
        call_args = system["mcp_service"].execute_cattackle.call_args

        payload = call_args.kwargs["payload"]
        assert payload["text"] == "Direct command text"
        assert payload["accumulated_params"] == []

    async def test_mixed_message_and_command_flow(self, integration_system):
        """Test alternating between message accumulation and command execution."""
        system = integration_system
        chat_id = 12345

        # Mixed updates: message → command → message → message → command
        mixed_updates = [
            {
                "update_id": 105,
                "message": {
                    "message_id": 205,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "First message",
                },
            },
            {
                "update_id": 106,
                "message": {
                    "message_id": 206,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "/echo First command",
                },
            },
            {
                "update_id": 107,
                "message": {
                    "message_id": 207,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "Second message",
                },
            },
            {
                "update_id": 108,
                "message": {
                    "message_id": 208,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "Third message",
                },
            },
            {
                "update_id": 109,
                "message": {
                    "message_id": 209,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "/echo Second command",
                },
            },
        ]

        system["telegram_client"].get_updates.return_value = mixed_updates
        await system["poller"]._run_single_loop()

        # Verify both commands were executed
        assert system["mcp_service"].execute_cattackle.call_count == 2

        # Check first command execution (with 1 accumulated parameter)
        first_call = system["mcp_service"].execute_cattackle.call_args_list[0]
        first_payload = first_call.kwargs["payload"]
        assert first_payload["text"] == "First command"
        assert first_payload["accumulated_params"] == ["First message"]

        # Check second command execution (with 2 accumulated parameters)
        second_call = system["mcp_service"].execute_cattackle.call_args_list[1]
        second_payload = second_call.kwargs["payload"]
        assert second_payload["text"] == "Second command"
        assert second_payload["accumulated_params"] == ["Second message", "Third message"]

        # Verify accumulator is empty after all commands
        remaining = system["accumulator_manager"]._accumulator.get_messages(chat_id)
        assert len(remaining) == 0


class TestChatIsolationIntegration:
    """Test that messages from different chats are properly isolated."""

    async def test_multiple_chats_message_isolation(self, integration_system):
        """Test that messages from different chats don't interfere with each other."""
        system = integration_system
        chat_id_1 = 11111
        chat_id_2 = 22222
        chat_id_3 = 33333

        # Messages from multiple chats
        multi_chat_updates = [
            {
                "update_id": 110,
                "message": {
                    "message_id": 210,
                    "chat": {"id": chat_id_1, "type": "private"},
                    "text": "Message for chat 1",
                },
            },
            {
                "update_id": 111,
                "message": {
                    "message_id": 211,
                    "chat": {"id": chat_id_2, "type": "private"},
                    "text": "Message for chat 2",
                },
            },
            {
                "update_id": 112,
                "message": {
                    "message_id": 212,
                    "chat": {"id": chat_id_1, "type": "private"},
                    "text": "Another message for chat 1",
                },
            },
            {
                "update_id": 113,
                "message": {
                    "message_id": 213,
                    "chat": {"id": chat_id_3, "type": "private"},
                    "text": "Message for chat 3",
                },
            },
        ]

        system["telegram_client"].get_updates.return_value = multi_chat_updates
        await system["poller"]._run_single_loop()

        # Verify messages are isolated by chat
        accumulator = system["accumulator_manager"]._accumulator

        chat1_messages = accumulator.get_messages(chat_id_1)
        chat2_messages = accumulator.get_messages(chat_id_2)
        chat3_messages = accumulator.get_messages(chat_id_3)

        assert len(chat1_messages) == 2
        assert chat1_messages == ["Message for chat 1", "Another message for chat 1"]

        assert len(chat2_messages) == 1
        assert chat2_messages == ["Message for chat 2"]

        assert len(chat3_messages) == 1
        assert chat3_messages == ["Message for chat 3"]

    async def test_command_execution_per_chat_isolation(self, integration_system):
        """Test that command execution only uses parameters from the same chat."""
        system = integration_system
        chat_id_1 = 11111
        chat_id_2 = 22222

        # Accumulate messages in both chats, then execute commands
        isolation_updates = [
            # Messages for chat 1
            {
                "update_id": 114,
                "message": {
                    "message_id": 214,
                    "chat": {"id": chat_id_1, "type": "private"},
                    "text": "Chat 1 param 1",
                },
            },
            {
                "update_id": 115,
                "message": {
                    "message_id": 215,
                    "chat": {"id": chat_id_1, "type": "private"},
                    "text": "Chat 1 param 2",
                },
            },
            # Messages for chat 2
            {
                "update_id": 116,
                "message": {
                    "message_id": 216,
                    "chat": {"id": chat_id_2, "type": "private"},
                    "text": "Chat 2 param 1",
                },
            },
            # Command in chat 1
            {
                "update_id": 117,
                "message": {
                    "message_id": 217,
                    "chat": {"id": chat_id_1, "type": "private"},
                    "text": "/echo Command from chat 1",
                },
            },
            # Command in chat 2
            {
                "update_id": 118,
                "message": {
                    "message_id": 218,
                    "chat": {"id": chat_id_2, "type": "private"},
                    "text": "/echo Command from chat 2",
                },
            },
        ]

        system["telegram_client"].get_updates.return_value = isolation_updates
        await system["poller"]._run_single_loop()

        # Verify both commands were executed with correct isolated parameters
        assert system["mcp_service"].execute_cattackle.call_count == 2

        # Check chat 1 command execution
        chat1_call = system["mcp_service"].execute_cattackle.call_args_list[0]
        chat1_payload = chat1_call.kwargs["payload"]
        assert chat1_payload["accumulated_params"] == ["Chat 1 param 1", "Chat 1 param 2"]

        # Check chat 2 command execution
        chat2_call = system["mcp_service"].execute_cattackle.call_args_list[1]
        chat2_payload = chat2_call.kwargs["payload"]
        assert chat2_payload["accumulated_params"] == ["Chat 2 param 1"]

        # Verify both accumulators are cleared
        accumulator = system["accumulator_manager"]._accumulator
        assert len(accumulator.get_messages(chat_id_1)) == 0
        assert len(accumulator.get_messages(chat_id_2)) == 0


class TestParameterExtractionVariations:
    """Test parameter extraction with various message counts and command requirements."""

    async def test_parameter_extraction_with_zero_messages(self, integration_system):
        """Test command execution when no messages are accumulated."""
        system = integration_system
        chat_id = 12345

        command_updates = [
            {
                "update_id": 119,
                "message": {
                    "message_id": 219,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "/echo No accumulated parameters",
                },
            }
        ]

        system["telegram_client"].get_updates.return_value = command_updates
        await system["poller"]._run_single_loop()

        # Verify command executed with empty parameters
        system["mcp_service"].execute_cattackle.assert_called_once()
        payload = system["mcp_service"].execute_cattackle.call_args.kwargs["payload"]
        assert payload["accumulated_params"] == []
        assert payload["text"] == "No accumulated parameters"

    async def test_parameter_extraction_with_single_message(self, integration_system):
        """Test command execution with exactly one accumulated message."""
        system = integration_system
        chat_id = 12345

        single_message_updates = [
            {
                "update_id": 120,
                "message": {
                    "message_id": 220,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "Single parameter",
                },
            },
            {
                "update_id": 121,
                "message": {
                    "message_id": 221,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "/echo Command with single param",
                },
            },
        ]

        system["telegram_client"].get_updates.return_value = single_message_updates
        await system["poller"]._run_single_loop()

        # Verify command executed with single parameter
        system["mcp_service"].execute_cattackle.assert_called_once()
        payload = system["mcp_service"].execute_cattackle.call_args.kwargs["payload"]
        assert payload["accumulated_params"] == ["Single parameter"]

    async def test_parameter_extraction_with_many_messages(self, integration_system):
        """Test command execution with many accumulated messages."""
        system = integration_system
        chat_id = 12345

        # Create 10 accumulated messages
        many_message_updates = []
        for i in range(10):
            many_message_updates.append(
                {
                    "update_id": 122 + i,
                    "message": {
                        "message_id": 222 + i,
                        "chat": {"id": chat_id, "type": "private"},
                        "text": f"Parameter {i + 1}",
                    },
                }
            )

        # Add command at the end
        many_message_updates.append(
            {
                "update_id": 132,
                "message": {
                    "message_id": 232,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "/echo Command with many params",
                },
            }
        )

        system["telegram_client"].get_updates.return_value = many_message_updates
        await system["poller"]._run_single_loop()

        # Verify command executed with all parameters
        system["mcp_service"].execute_cattackle.assert_called_once()
        payload = system["mcp_service"].execute_cattackle.call_args.kwargs["payload"]
        expected_params = [f"Parameter {i + 1}" for i in range(10)]
        assert payload["accumulated_params"] == expected_params

    async def test_parameter_extraction_with_empty_and_whitespace_messages(self, integration_system):
        """Test that empty and whitespace messages are filtered during parameter extraction."""
        system = integration_system
        chat_id = 12345

        mixed_quality_updates = [
            {
                "update_id": 133,
                "message": {
                    "message_id": 233,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "Valid parameter 1",
                },
            },
            {
                "update_id": 134,
                "message": {
                    "message_id": 234,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "",  # Empty message
                },
            },
            {
                "update_id": 135,
                "message": {
                    "message_id": 235,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "   ",  # Whitespace only
                },
            },
            {
                "update_id": 136,
                "message": {
                    "message_id": 236,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "Valid parameter 2",
                },
            },
            {
                "update_id": 137,
                "message": {
                    "message_id": 237,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "/echo Command after filtering",
                },
            },
        ]

        system["telegram_client"].get_updates.return_value = mixed_quality_updates
        await system["poller"]._run_single_loop()

        # Verify only valid messages were accumulated and passed as parameters
        system["mcp_service"].execute_cattackle.assert_called_once()
        payload = system["mcp_service"].execute_cattackle.call_args.kwargs["payload"]
        assert payload["accumulated_params"] == ["Valid parameter 1", "Valid parameter 2"]


class TestSystemCommandsIntegration:
    """Test system commands integration with real accumulator state."""

    async def test_show_accumulator_command_integration(self, integration_system):
        """Test /show_accumulator command with real accumulator state."""
        system = integration_system
        chat_id = 12345

        # First accumulate some messages
        accumulation_updates = [
            {
                "update_id": 138,
                "message": {
                    "message_id": 238,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "Message 1 for display",
                },
            },
            {
                "update_id": 139,
                "message": {
                    "message_id": 239,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "Message 2 for display",
                },
            },
        ]

        system["telegram_client"].get_updates.return_value = accumulation_updates
        await system["poller"]._run_single_loop()

        # Execute show_accumulator command
        show_command_updates = [
            {
                "update_id": 140,
                "message": {
                    "message_id": 240,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "/show_accumulator",
                },
            }
        ]

        system["telegram_client"].get_updates.return_value = show_command_updates
        await system["poller"]._run_single_loop()

        # Verify show command response was sent
        system["telegram_client"].send_message.assert_called()
        last_call = system["telegram_client"].send_message.call_args_list[-1]
        response_text = last_call[0][1]

        assert "Your accumulated messages (2 total)" in response_text
        assert "Message 1 for display" in response_text
        assert "Message 2 for display" in response_text

        # Verify messages are still in accumulator (show doesn't clear)
        remaining = system["accumulator_manager"]._accumulator.get_messages(chat_id)
        assert len(remaining) == 2

    async def test_clear_accumulator_command_integration(self, integration_system):
        """Test /clear_accumulator command with real accumulator state."""
        system = integration_system
        chat_id = 12345

        # First accumulate some messages
        accumulation_updates = [
            {
                "update_id": 141,
                "message": {
                    "message_id": 241,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "Message to be cleared",
                },
            },
            {
                "update_id": 142,
                "message": {
                    "message_id": 242,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "Another message to be cleared",
                },
            },
        ]

        system["telegram_client"].get_updates.return_value = accumulation_updates
        await system["poller"]._run_single_loop()

        # Verify messages were accumulated
        assert len(system["accumulator_manager"]._accumulator.get_messages(chat_id)) == 2

        # Execute clear_accumulator command
        clear_command_updates = [
            {
                "update_id": 143,
                "message": {
                    "message_id": 243,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "/clear_accumulator",
                },
            }
        ]

        system["telegram_client"].get_updates.return_value = clear_command_updates
        await system["poller"]._run_single_loop()

        # Verify clear command response was sent
        system["telegram_client"].send_message.assert_called()
        last_call = system["telegram_client"].send_message.call_args_list[-1]
        response_text = last_call[0][1]
        assert "Cleared 2 accumulated messages" in response_text

        # Verify accumulator is actually cleared
        remaining = system["accumulator_manager"]._accumulator.get_messages(chat_id)
        assert len(remaining) == 0

    async def test_accumulator_status_command_integration(self, integration_system):
        """Test /accumulator_status command with real accumulator state."""
        system = integration_system
        chat_id = 12345

        # Test status with empty accumulator
        empty_status_updates = [
            {
                "update_id": 144,
                "message": {
                    "message_id": 244,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "/accumulator_status",
                },
            }
        ]

        system["telegram_client"].get_updates.return_value = empty_status_updates
        await system["poller"]._run_single_loop()

        # Verify empty status response
        system["telegram_client"].send_message.assert_called()
        empty_response = system["telegram_client"].send_message.call_args[0][1]
        assert "📭 No messages accumulated" in empty_response

        # Accumulate some messages
        accumulation_updates = [
            {
                "update_id": 145,
                "message": {
                    "message_id": 245,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "Status test message 1",
                },
            },
            {
                "update_id": 146,
                "message": {
                    "message_id": 246,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "Status test message 2",
                },
            },
            {
                "update_id": 147,
                "message": {
                    "message_id": 247,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "Status test message 3",
                },
            },
        ]

        system["telegram_client"].get_updates.return_value = accumulation_updates
        await system["poller"]._run_single_loop()

        # Test status with accumulated messages
        status_updates = [
            {
                "update_id": 148,
                "message": {
                    "message_id": 248,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "/accumulator_status",
                },
            }
        ]

        system["telegram_client"].get_updates.return_value = status_updates
        await system["poller"]._run_single_loop()

        # Verify status response with messages
        last_call = system["telegram_client"].send_message.call_args_list[-1]
        status_response = last_call[0][1]
        assert "📝 You have 3 messages accumulated" in status_response

    async def test_system_commands_do_not_route_to_cattackles(self, integration_system):
        """Test that system commands are handled directly and not routed to cattackles."""
        system = integration_system
        chat_id = 12345

        # Execute all system commands
        system_command_updates = [
            {
                "update_id": 149,
                "message": {
                    "message_id": 249,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "/show_accumulator",
                },
            },
            {
                "update_id": 150,
                "message": {
                    "message_id": 250,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "/clear_accumulator",
                },
            },
            {
                "update_id": 151,
                "message": {
                    "message_id": 251,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "/accumulator_status",
                },
            },
        ]

        system["telegram_client"].get_updates.return_value = system_command_updates
        await system["poller"]._run_single_loop()

        # Verify no cattackle executions were triggered
        system["mcp_service"].execute_cattackle.assert_not_called()

        # Verify responses were sent for all system commands
        assert system["telegram_client"].send_message.call_count == 3


class TestBackwardCompatibility:
    """Test backward compatibility with existing cattackle implementations."""

    async def test_cattackle_receives_expected_payload_format(self, integration_system):
        """Test that cattackles receive the expected payload format with accumulated_params."""
        system = integration_system
        chat_id = 12345

        # Accumulate messages and execute command
        compatibility_updates = [
            {
                "update_id": 152,
                "message": {
                    "message_id": 252,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "Compatibility test param",
                },
            },
            {
                "update_id": 153,
                "message": {
                    "message_id": 253,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "/echo Compatibility test command",
                },
            },
        ]

        system["telegram_client"].get_updates.return_value = compatibility_updates
        await system["poller"]._run_single_loop()

        # Verify payload format includes all expected fields
        system["mcp_service"].execute_cattackle.assert_called_once()
        payload = system["mcp_service"].execute_cattackle.call_args.kwargs["payload"]

        # Verify backward compatibility fields are present
        assert "text" in payload
        assert "message" in payload
        assert payload["text"] == "Compatibility test command"

        # Verify new accumulated_params field is present
        assert "accumulated_params" in payload
        assert payload["accumulated_params"] == ["Compatibility test param"]

        # Verify message field contains full Telegram message
        assert payload["message"]["chat"]["id"] == chat_id
        assert payload["message"]["text"] == "/echo Compatibility test command"

    async def test_legacy_command_format_still_works(self, integration_system):
        """Test that commands without accumulated parameters work as before."""
        system = integration_system
        chat_id = 12345

        # Execute command in legacy style (no accumulated parameters)
        legacy_updates = [
            {
                "update_id": 154,
                "message": {
                    "message_id": 254,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "/echo Legacy command with inline parameters",
                },
            }
        ]

        system["telegram_client"].get_updates.return_value = legacy_updates
        await system["poller"]._run_single_loop()

        # Verify command executed in legacy format
        system["mcp_service"].execute_cattackle.assert_called_once()
        payload = system["mcp_service"].execute_cattackle.call_args.kwargs["payload"]

        assert payload["text"] == "Legacy command with inline parameters"
        assert payload["accumulated_params"] == []  # Empty but present
        assert "message" in payload

    async def test_mixed_legacy_and_accumulated_parameter_usage(self, integration_system):
        """Test that both legacy and accumulated parameter styles can be used interchangeably."""
        system = integration_system
        chat_id = 12345

        # Mixed usage: legacy → accumulated → legacy
        mixed_updates = [
            # Legacy command
            {
                "update_id": 155,
                "message": {
                    "message_id": 255,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "/echo First legacy command",
                },
            },
            # Accumulate parameters
            {
                "update_id": 156,
                "message": {
                    "message_id": 256,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "Accumulated param 1",
                },
            },
            {
                "update_id": 157,
                "message": {
                    "message_id": 257,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "Accumulated param 2",
                },
            },
            # Command with accumulated parameters
            {
                "update_id": 158,
                "message": {
                    "message_id": 258,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "/echo Command with accumulated",
                },
            },
            # Another legacy command
            {
                "update_id": 159,
                "message": {
                    "message_id": 259,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "/echo Second legacy command",
                },
            },
        ]

        system["telegram_client"].get_updates.return_value = mixed_updates
        await system["poller"]._run_single_loop()

        # Verify all three commands were executed
        assert system["mcp_service"].execute_cattackle.call_count == 3

        # Check first legacy command
        first_call = system["mcp_service"].execute_cattackle.call_args_list[0]
        first_payload = first_call.kwargs["payload"]
        assert first_payload["text"] == "First legacy command"
        assert first_payload["accumulated_params"] == []

        # Check accumulated parameter command
        second_call = system["mcp_service"].execute_cattackle.call_args_list[1]
        second_payload = second_call.kwargs["payload"]
        assert second_payload["text"] == "Command with accumulated"
        assert second_payload["accumulated_params"] == ["Accumulated param 1", "Accumulated param 2"]

        # Check second legacy command
        third_call = system["mcp_service"].execute_cattackle.call_args_list[2]
        third_payload = third_call.kwargs["payload"]
        assert third_payload["text"] == "Second legacy command"
        assert third_payload["accumulated_params"] == []

    async def test_cattackle_registry_compatibility(self, integration_system):
        """Test that the cattackle registry works correctly with the new message router."""
        system = integration_system
        chat_id = 12345

        # Test that registry commands are properly resolved
        registry_test_updates = [
            {
                "update_id": 160,
                "message": {
                    "message_id": 260,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "/echo Registry compatibility test",
                },
            }
        ]

        system["telegram_client"].get_updates.return_value = registry_test_updates
        await system["poller"]._run_single_loop()

        # Verify command was resolved through registry and executed
        system["mcp_service"].execute_cattackle.assert_called_once()
        call_args = system["mcp_service"].execute_cattackle.call_args

        assert call_args.kwargs["command"] == "echo"
        assert call_args.kwargs["cattackle_config"] is not None

        # Verify cattackle_config comes from registry
        cattackle_config = call_args.kwargs["cattackle_config"]
        assert cattackle_config.name == "echo"
        assert "echo" in cattackle_config.commands

    async def test_error_handling_compatibility(self, integration_system):
        """Test that error handling works correctly with accumulated parameters."""
        from catmandu.core.errors import CattackleExecutionError

        system = integration_system
        chat_id = 12345

        # Configure mock to raise a CattackleExecutionError (which is caught by router)
        system["mcp_service"].execute_cattackle.side_effect = CattackleExecutionError("Test cattackle error")

        # Accumulate parameters and execute command that will fail
        error_test_updates = [
            {
                "update_id": 161,
                "message": {
                    "message_id": 261,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "Parameter for failing command",
                },
            },
            {
                "update_id": 162,
                "message": {
                    "message_id": 262,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": "/echo This command will fail",
                },
            },
        ]

        system["telegram_client"].get_updates.return_value = error_test_updates
        await system["poller"]._run_single_loop()

        # Verify command was attempted
        system["mcp_service"].execute_cattackle.assert_called_once()

        # Verify error response was sent
        system["telegram_client"].send_message.assert_called()
        error_call = system["telegram_client"].send_message.call_args_list[-1]
        error_response = error_call[0][1]
        assert "An error occurred while executing the command" in error_response

        # Verify accumulator was still cleared even after error
        remaining = system["accumulator_manager"]._accumulator.get_messages(chat_id)
        assert len(remaining) == 0
