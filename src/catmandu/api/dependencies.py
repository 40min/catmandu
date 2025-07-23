from fastapi import Request

from catmandu.core.clients import TelegramClient
from catmandu.core.services import CattackleRegistry, McpService, MessageRouter


def get_cattackle_registry(request: Request) -> CattackleRegistry:
    """Returns the cattackle registry instance from the app state."""
    return request.app.state.cattackle_registry


def get_mcp_service(request: Request) -> McpService:
    """Returns the MCP service instance from the app state."""
    return request.app.state.mcp_service


def get_message_router(request: Request) -> MessageRouter:
    """Returns the message router instance from the app state."""
    return request.app.state.message_router


def get_telegram_client(request: Request) -> TelegramClient:
    """Returns the telegram client instance from the app state."""
    return request.app.state.telegram_client
