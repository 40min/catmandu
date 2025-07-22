import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from catmandu.api import admin, cattackles, health
from catmandu.core.config import Settings
from catmandu.core.services.mcp_client import McpClientManager
from catmandu.core.services.poller import TelegramPoller
from catmandu.core.services.registry import CattackleRegistry
from catmandu.core.services.router import MessageRouter
from catmandu.core.services.telegram import TelegramService
from catmandu.logging import configure_logging

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    log.info("Starting Catmandu Core")
    settings = Settings()  # type: ignore

    # Initialize services
    cattackle_registry = CattackleRegistry(config=settings)
    cattackle_registry.scan()
    mcp_client_manager = McpClientManager()
    telegram_service = TelegramService(token=settings.telegram_bot_token)
    message_router = MessageRouter(mcp_client_manager=mcp_client_manager, cattackle_registry=cattackle_registry)
    poller = TelegramPoller(router=message_router, telegram_service=telegram_service, settings=settings)

    # Store services in app state for DI
    app.state.cattackle_registry = cattackle_registry
    app.state.mcp_client_manager = mcp_client_manager
    app.state.message_router = message_router
    app.state.telegram_service = telegram_service
    app.state.poller = poller

    poller_task = asyncio.create_task(poller.run())

    try:
        yield
    finally:
        # Shutdown
        log.info("Shutting down Catmandu Core")
        await poller.stop()
        await poller_task
        await telegram_service.close()
        # Clean up all MCP client sessions
        await mcp_client_manager.close_all_sessions()


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(
        title="Catmandu Core",
        description="The core service for the Catmandu modular Telegram bot.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(health.router)
    app.include_router(cattackles.router)
    app.include_router(admin.router)
    return app
