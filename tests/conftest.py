import logging

import pytest
from httpx import ASGITransport, AsyncClient
from loguru import logger

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


@pytest.fixture
def caplog_setup_for_loguru(caplog):
    """Fixture to set up loguru to output to caplog."""
    caplog.set_level(logging.DEBUG)

    class CaplogHandler(logging.Handler):
        def emit(self, record):
            caplog.handler.emit(record)

    handler = CaplogHandler()
    handler.setLevel(logging.DEBUG)

    # Add handler to the root logger to capture all logs
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    # Also configure loguru to use the same handler
    logger.remove()
    logger.configure(handlers=[{"sink": handler, "level": 0}])

    yield

    # Clean up
    root_logger.removeHandler(handler)
