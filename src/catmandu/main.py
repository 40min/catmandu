import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from catmandu.api import admin, cattackles, health
from catmandu.core.audio_processor import AudioProcessor
from catmandu.core.clients.mcp import McpClient
from catmandu.core.clients.telegram import TelegramClient
from catmandu.core.config import Settings
from catmandu.core.cost_tracker import CostTracker
from catmandu.core.infrastructure.chat_logger import ChatLogger
from catmandu.core.infrastructure.mcp_manager import McpService
from catmandu.core.infrastructure.poller import TelegramPoller
from catmandu.core.infrastructure.registry import CattackleRegistry
from catmandu.core.infrastructure.router import MessageRouter
from catmandu.core.services.accumulator import MessageAccumulator
from catmandu.core.services.accumulator_manager import AccumulatorManager
from catmandu.logging import configure_logging

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    log.info("Starting Catmandu Core")
    try:
        settings = Settings()  # type: ignore
        settings.validate_environment()
    except Exception as e:
        log.error(f"Configuration validation failed: {e}")
        raise

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
    accumulator_manager = AccumulatorManager(accumulator=message_accumulator, feedback_enabled=False)

    # Initialize chat logger
    chat_logger = ChatLogger(logs_dir=settings.chat_logs_dir)

    # Initialize audio processing components if enabled
    audio_processor = None
    cost_tracker = None
    if settings.is_audio_processing_available():
        log.info("Audio processing is enabled and properly configured, initializing audio processor")
        try:
            cost_tracker = CostTracker(settings=settings)
            audio_processor = AudioProcessor(
                settings=settings,
                telegram_client=telegram_client,
                cost_tracker=cost_tracker,
            )
            log.info("Audio processor initialized successfully")
        except Exception as e:
            log.error(f"Failed to initialize audio processor: {e}")
            log.warning("Audio processing will be disabled for this session")
            audio_processor = None
            cost_tracker = None
    else:
        log.info(settings.get_audio_processing_status_message())

    # Initialize router with accumulator manager, chat logger, and optional audio processor
    message_router = MessageRouter(
        mcp_service=mcp_service,
        cattackle_registry=cattackle_registry,
        accumulator_manager=accumulator_manager,
        chat_logger=chat_logger,
        audio_processor=audio_processor,
    )
    poller = TelegramPoller(router=message_router, telegram_client=telegram_client, settings=settings)

    # Store services in app state for DI
    app.state.cattackle_registry = cattackle_registry
    app.state.mcp_service = mcp_service
    app.state.message_accumulator = message_accumulator
    app.state.accumulator_manager = accumulator_manager
    app.state.chat_logger = chat_logger
    app.state.message_router = message_router
    app.state.telegram_client = telegram_client
    app.state.poller = poller
    app.state.audio_processor = audio_processor
    app.state.cost_tracker = cost_tracker

    poller_task = asyncio.create_task(poller.run())

    try:
        yield
    finally:
        # Shutdown
        log.info("Shutting down Catmandu Core")
        await poller.stop()
        await poller_task
        await telegram_client.close()
        # Clean up audio processor if it exists
        if audio_processor:
            await audio_processor.close()
        # Clean up all MCP client sessions
        await mcp_service.close_all_sessions()


def create_app() -> FastAPI:
    # Load settings early to get log level
    settings = Settings()
    configure_logging(settings.log_level)

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
