"""Integration tests for dependency injection and component interaction."""

import pytest

from catmandu.core.services.accumulator import MessageAccumulator
from catmandu.core.services.accumulator_manager import AccumulatorManager
from catmandu.core.services.registry import CattackleRegistry
from catmandu.core.services.router import MessageRouter
from catmandu.main import create_app


class TestDependencyInjection:
    """Test that all components are properly instantiated and wired together."""

    def test_app_creation_succeeds(self):
        """Test that the FastAPI app can be created without errors."""
        app = create_app()
        assert app is not None
        assert app.title == "Catmandu Core"

    @pytest.mark.asyncio
    async def test_lifespan_initializes_all_services(self):
        """Test that the lifespan context manager initializes all required services."""
        app = create_app()

        # Simulate lifespan startup
        async with app.router.lifespan_context(app):
            # Verify all services are initialized in app state
            assert hasattr(app.state, "cattackle_registry")
            assert hasattr(app.state, "mcp_service")
            assert hasattr(app.state, "message_accumulator")
            assert hasattr(app.state, "accumulator_manager")
            assert hasattr(app.state, "message_router")
            assert hasattr(app.state, "telegram_client")
            assert hasattr(app.state, "poller")

            # Verify service types
            assert isinstance(app.state.message_accumulator, MessageAccumulator)
            assert isinstance(app.state.accumulator_manager, AccumulatorManager)
            assert isinstance(app.state.cattackle_registry, CattackleRegistry)
            assert isinstance(app.state.message_router, MessageRouter)

    @pytest.mark.asyncio
    async def test_service_dependency_chain(self):
        """Test that services are properly wired with their dependencies."""
        app = create_app()

        async with app.router.lifespan_context(app):
            # Test MessageAccumulator configuration
            accumulator = app.state.message_accumulator
            assert accumulator._max_messages == 100
            assert accumulator._max_message_length == 1000

            # Test AccumulatorManager has correct accumulator dependency
            manager = app.state.accumulator_manager
            assert manager._accumulator is accumulator
            assert manager._feedback_enabled is False

            # Test MessageRouter has correct dependencies
            router = app.state.message_router
            assert router._accumulator_manager is manager
            assert router._registry is app.state.cattackle_registry
            assert router._mcp_service is app.state.mcp_service

    @pytest.mark.asyncio
    async def test_accumulator_integration_with_router(self):
        """Test that the accumulator integrates properly with the message router."""
        app = create_app()

        async with app.router.lifespan_context(app):
            router = app.state.message_router
            accumulator = app.state.message_accumulator

            # Test non-command message processing
            chat_id = 12345
            test_message = "This is a test message"

            # Create a mock update for non-command message
            update = {"message": {"chat": {"id": chat_id}, "text": test_message}}

            # Process the update
            result = await router.process_update(update)

            # Verify message was accumulated
            messages = accumulator.get_messages(chat_id)
            assert len(messages) == 1
            assert messages[0] == test_message

            # Verify no feedback was returned (since feedback_enabled=False by default)
            assert result is None

    @pytest.mark.asyncio
    async def test_system_commands_integration(self):
        """Test that system commands work through the integrated router."""
        app = create_app()

        async with app.router.lifespan_context(app):
            router = app.state.message_router
            chat_id = 12345

            # First accumulate some messages
            for i in range(3):
                update = {"message": {"chat": {"id": chat_id}, "text": f"Test message {i+1}"}}
                await router.process_update(update)

            # Test accumulator_status command
            status_update = {"message": {"chat": {"id": chat_id}, "text": "/accumulator_status"}}
            result = await router.process_update(status_update)
            assert result is not None
            chat_id_result, status_response = result
            assert chat_id_result == chat_id
            assert "3 messages accumulated" in status_response

            # Test show_accumulator command
            show_update = {"message": {"chat": {"id": chat_id}, "text": "/show_accumulator"}}
            result = await router.process_update(show_update)
            assert result is not None
            chat_id_result, show_response = result
            assert chat_id_result == chat_id
            assert "Your accumulated messages (3 total)" in show_response
            assert "Test message 1" in show_response

            # Test clear_accumulator command
            clear_update = {"message": {"chat": {"id": chat_id}, "text": "/clear_accumulator"}}
            result = await router.process_update(clear_update)
            assert result is not None
            chat_id_result, clear_response = result
            assert chat_id_result == chat_id
            assert "Cleared 3 accumulated messages" in clear_response

            # Verify accumulator is actually cleared
            accumulator = app.state.message_accumulator
            assert accumulator.get_message_count(chat_id) == 0

    @pytest.mark.asyncio
    async def test_chat_isolation_integration(self):
        """Test that chat isolation works properly in the integrated system."""
        app = create_app()

        async with app.router.lifespan_context(app):
            router = app.state.message_router
            accumulator = app.state.message_accumulator

            chat_id_1 = 11111
            chat_id_2 = 22222

            # Add messages to different chats
            update_1 = {"message": {"chat": {"id": chat_id_1}, "text": "Message for chat 1"}}
            update_2 = {"message": {"chat": {"id": chat_id_2}, "text": "Message for chat 2"}}

            await router.process_update(update_1)
            await router.process_update(update_2)

            # Verify isolation
            messages_1 = accumulator.get_messages(chat_id_1)
            messages_2 = accumulator.get_messages(chat_id_2)

            assert len(messages_1) == 1
            assert len(messages_2) == 1
            assert messages_1[0] == "Message for chat 1"
            assert messages_2[0] == "Message for chat 2"

            # Clear one chat and verify the other is unaffected
            clear_update = {"message": {"chat": {"id": chat_id_1}, "text": "/clear_accumulator"}}
            await router.process_update(clear_update)

            assert accumulator.get_message_count(chat_id_1) == 0
            assert accumulator.get_message_count(chat_id_2) == 1
            assert accumulator.get_messages(chat_id_2)[0] == "Message for chat 2"

    @pytest.mark.asyncio
    async def test_memory_limits_integration(self):
        """Test that memory limits are enforced in the integrated system."""
        app = create_app()

        async with app.router.lifespan_context(app):
            router = app.state.message_router
            accumulator = app.state.message_accumulator
            chat_id = 12345

            # Add more messages than the limit (100)
            for i in range(105):
                update = {"message": {"chat": {"id": chat_id}, "text": f"Message {i+1}"}}
                await router.process_update(update)

            # Verify limit is enforced
            messages = accumulator.get_messages(chat_id)
            assert len(messages) == 100

            # Verify we kept the most recent messages
            assert messages[0] == "Message 6"  # First 5 were removed
            assert messages[-1] == "Message 105"  # Last message is kept
