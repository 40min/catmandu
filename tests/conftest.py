import logging
import os
from unittest.mock import patch

import pytest
import structlog
from httpx import ASGITransport, AsyncClient

from catmandu.main import create_app

# A valid cattackle.toml content
VALID_CATTACKLE_TOML = """
[cattackle]
name = "echo"
version = "0.1.0"
description = "A simple echo cattackle."

[cattackle.commands.echo]
description = "Echoes back the payload."

[cattackle.mcp.transport]
type = "stdio"
command = "python"
args = ["-m", "cattackles.echo.src.server"]
"""

# Another valid cattackle.toml for testing duplicates
VALID_CATTACKLE_TOML_2 = """
[cattackle]
name = "admin"
version = "0.1.0"
description = "An admin cattackle."

[cattackle.commands.reload]
description = "Reloads cattackles."

[cattackle.commands.echo]
description = "A duplicate echo command."

[cattackle.mcp.transport]
type = "stdio"
command = "python"
args = ["-m", "cattackles.admin.src.server"]
"""

# A malformed TOML file
INVALID_TOML = """
[cattackle
name = "bad"
"""

# A TOML with missing required fields (validation error)
INVALID_CONFIG_TOML = """
[cattackle]
name = "invalid"
version = "0.1.0"
"""


@pytest.fixture
def mock_cattackle_toml(fs):
    """Fixture to create a virtual cattackle.toml file."""

    def _mock_cattackle_toml(path, contents):
        fs.create_file(path, contents=contents)
        return path

    return _mock_cattackle_toml


@pytest.fixture
def valid_cattackle_toml_file(mock_cattackle_toml):
    """Provides a path to a virtual valid cattackle.toml file."""
    return mock_cattackle_toml("/cattackles/echo/cattackle.toml", VALID_CATTACKLE_TOML)


@pytest.fixture
def valid_cattackle_toml_2_file(mock_cattackle_toml):
    """Provides a path to a virtual second valid cattackle.toml file."""
    return mock_cattackle_toml("/cattackles/admin/cattackle.toml", VALID_CATTACKLE_TOML_2)


@pytest.fixture
def invalid_toml_file(mock_cattackle_toml):
    """Provides a path to a virtual malformed TOML file."""
    return mock_cattackle_toml("/cattackles/bad/cattackle.toml", INVALID_TOML)


@pytest.fixture
def invalid_config_toml_file(mock_cattackle_toml):
    """Provides a path to a virtual TOML file with missing required fields."""
    return mock_cattackle_toml("/cattackles/invalid/cattackle.toml", INVALID_CONFIG_TOML)


@pytest.fixture
def app_test():
    """Get test app"""
    return create_app()


@pytest.fixture
async def async_client(app_test):
    """Get async test client"""
    async with AsyncClient(transport=ASGITransport(app=app_test), base_url="http://test") as client:
        yield client


@pytest.fixture
def test_registry_with_cattackles(valid_cattackle_toml_file):
    """Create a registry with cattackles for testing."""
    from catmandu.core.config import Settings
    from catmandu.core.infrastructure.registry import CattackleRegistry

    settings = Settings()
    registry = CattackleRegistry(config=settings)
    registry.scan()
    return registry


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up required environment variables for all tests."""
    test_env = {
        "TELEGRAM_BOT_TOKEN": "test_bot_token_123",
        "GEMINI_API_KEY": "test_gemini_api_key",
        "GEMINI_MODEL": "gemini-2.5-flash-lite-preview-06-17",
    }

    with patch.dict(os.environ, test_env, clear=False):
        yield


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
