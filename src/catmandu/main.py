import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from catmandu.api import admin, cattackles, health
from catmandu.core.clients.mcp import McpClient
from catmandu.core.clients.telegram import TelegramClient
from catmandu.core.config import Settings
from catmandu.core.services.accumulator import MessageAccumulator
from catmandu.core.services.accumulator_manager import AccumulatorManager
from catmandu.core.services.mcp_service import McpService
from catmandu.core.services.poller import TelegramPoller
from catmandu.core.services.registry import CattackleRegistry
from catmandu.core.services.router import MessageRouter
from catmandu.logging import configure_logging

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    log.info("Starting Catmandu Core")
    settings = Settings()  # type: ignore

    # Initialize clients
    telegram_client = TelegramClient(token=settings.telegram_bot_token)
    mcp_client = McpClient()

    # Initialize services in proper dependency order
    cattackle_registry = CattackleRegistry(config=settings)
    cattackle_registry.scan()
    mcp_service = McpService(mcp_client=mcp_client)

    # Initialize accumulator services
    message_accumulator = MessageAccumulator(
        max_messages_per_chat=settings.max_messages_per_chat, max_message_length=settings.max_message_length
    )
    accumulator_manager = AccumulatorManager(accumulator=message_accumulator, feedback_enabled=True)

    # Initialize router with accumulator manager dependency
    message_router = MessageRouter(
        mcp_service=mcp_service, cattackle_registry=cattackle_registry, accumulator_manager=accumulator_manager
    )
    poller = TelegramPoller(router=message_router, telegram_client=telegram_client, settings=settings)

    # Store services in app state for DI
    app.state.cattackle_registry = cattackle_registry
    app.state.mcp_service = mcp_service
    app.state.message_accumulator = message_accumulator
    app.state.accumulator_manager = accumulator_manager
    app.state.message_router = message_router
    app.state.telegram_client = telegram_client
    app.state.poller = poller

    poller_task = asyncio.create_task(poller.run())

    try:
        yield
    finally:
        # Shutdown
        log.info("Shutting down Catmandu Core")
        await poller.stop()
        await poller_task
        await telegram_client.close()
        # Clean up all MCP client sessions
        await mcp_service.close_all_sessions()


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
