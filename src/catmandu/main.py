from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from catmandu.api import admin, cattackles, health
from catmandu.core.config import Settings
from catmandu.core.services.registry import CattackleRegistry
from catmandu.logging import configure_logging

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    log.info("Starting Catmandu Core")
    settings = Settings()
    registry = CattackleRegistry(config=settings)
    registry.scan()
    app.state.cattackle_registry = registry
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
    app.include_router(cattackles.router)
    app.include_router(admin.router)
    return app


if __name__ == "__main__":
    app = create_app()
