import logging

import pytest
import structlog
from httpx import ASGITransport, AsyncClient

from catmandu.main import create_app


@pytest.fixture
def app_test():
    """Get test app"""
    return create_app()


@pytest.fixture
async def async_client(app_test):  # Depends on clean_db for per-test cleanup
    """Get async test client"""
    async with AsyncClient(
        transport=ASGITransport(app=app_test), base_url="http://test"
    ) as client:
        yield client


@pytest.fixture(autouse=True)
def caplog_setup_for_structlog(caplog):
    """Fixture to capture structlog logs in caplog."""

    # Store original configuration
    original_config = structlog.get_config()

    # Configure structlog to use Python's logging module
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),  # Use stdlib logger factory
        cache_logger_on_first_use=True,
    )

    # Set caplog to capture DEBUG and above
    caplog.set_level(logging.DEBUG)

    # Set root logger level to DEBUG
    logging.getLogger().setLevel(logging.DEBUG)

    yield

    # Restore original configuration
    structlog.configure(**original_config)
