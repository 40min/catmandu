from unittest.mock import AsyncMock

import pytest

from catmandu.core.models import CattackleResponse

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_telegram_service():
    service = AsyncMock()
    service.get_updates.return_value = [
        {
            "update_id": 123,
            "message": {
                "message_id": 456,
                "chat": {"id": 789, "type": "private"},
                "text": "/echo Hello World",
            },
        }
    ]
    return service


@pytest.fixture
def mock_mcp_client_manager():
    manager = AsyncMock()
    manager.call.return_value = CattackleResponse(data={"text": "Echo: Hello World"})
    return manager


@pytest.fixture
def app_test_with_mocks(
    app_test,
    test_registry_with_cattackles,
    mock_telegram_service,
    mock_mcp_client_manager,
):
    """Override services in app state for integration testing."""
    from catmandu.core.config import Settings
    from catmandu.core.services.poller import TelegramPoller
    from catmandu.core.services.router import MessageRouter

    # Initialize services manually since lifespan doesn't run in tests
    settings = Settings()
    message_router = MessageRouter(
        mcp_client_manager=mock_mcp_client_manager, cattackle_registry=test_registry_with_cattackles
    )
    poller = TelegramPoller(router=message_router, telegram_service=mock_telegram_service, settings=settings)

    # Store services in app state
    app_test.state.cattackle_registry = test_registry_with_cattackles
    app_test.state.mcp_client_manager = mock_mcp_client_manager
    app_test.state.message_router = message_router
    app_test.state.telegram_service = mock_telegram_service
    app_test.state.poller = poller

    return app_test


async def test_end_to_end_message_flow(app_test_with_mocks):
    poller = app_test_with_mocks.state.poller
    mock_telegram_service = app_test_with_mocks.state.telegram_service
    mock_mcp_client_manager = app_test_with_mocks.state.mcp_client_manager

    # Run one iteration of the poller loop
    await poller._run_single_loop()

    # Assertions
    mock_telegram_service.get_updates.assert_called_once()
    mock_mcp_client_manager.call.assert_called_once()

    call_args = mock_mcp_client_manager.call.call_args
    assert call_args.kwargs["command"] == "echo"
    assert call_args.kwargs["payload"]["text"] == "Hello World"

    mock_telegram_service.send_message.assert_called_once_with(789, "{'text': 'Echo: Hello World'}")
