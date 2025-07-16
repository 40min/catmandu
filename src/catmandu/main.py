from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from catmandu.api import health
from catmandu.logging import configure_logging

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    log.info("Starting Catmandu Core")
    yield
    # Shutdown
    log.info("Shutting down Catmandu Core")


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(
        title="Catmandu Core",
        description="The core service for the Catmandu modular Telegram bot.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(health.router)
    return app


app = create_app()
