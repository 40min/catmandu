from contextlib import asynccontextmanager
from typing import Optional

import structlog
from fastapi import FastAPI

from catmandu.api import cattackles, health
from catmandu.core.services.registry import CattackleRegistry
from catmandu.logging import configure_logging

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI, cattackles_dir: Optional[str] = None):
    # Startup
    log.info("Starting Catmandu Core")
    registry = CattackleRegistry(cattackles_dir=cattackles_dir)
    registry.scan()
    app.state.registry = registry
    yield
    # Shutdown
    log.info("Shutting down Catmandu Core")


def create_app(cattackles_dir: Optional[str] = None) -> FastAPI:
    configure_logging()
    app = FastAPI(
        title="Catmandu Core",
        description="The core service for the Catmandu modular Telegram bot.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.cattackles_dir = cattackles_dir
    app.include_router(health.router)
    app.include_router(cattackles.router)
    return app


if __name__ == "__main__":
    app = create_app()
