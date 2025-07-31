"""
Common test fixtures for the echo cattackle test suite.
These fixtures are available to all test modules.
"""

from unittest.mock import MagicMock

import pytest
from echo.clients.gemini_client import GeminiClient
from echo.config import EchoCattackleSettings
from echo.core.cattackle import EchoCattackle


# Common test data fixtures
@pytest.fixture
def test_api_key():
    """Standard test API key."""
    return "test-api-key"


@pytest.fixture
def test_model_name():
    """Standard test model name."""
    return "gemini-pro"


@pytest.fixture
def test_port():
    """Standard test port."""
    return 8001


# Settings fixtures
@pytest.fixture
def valid_settings():
    """Create valid settings for testing."""
    return EchoCattackleSettings(
        gemini_api_key="test-api-key", gemini_model="gemini-pro", mcp_server_port=8001, log_level="INFO"
    )


@pytest.fixture
def settings_with_gemini(test_api_key, test_model_name, test_port):
    """Create settings with Gemini configuration."""
    return EchoCattackleSettings(
        gemini_api_key=test_api_key, gemini_model=test_model_name, mcp_server_port=test_port, log_level="INFO"
    )


@pytest.fixture
def settings_without_gemini(test_model_name, test_port):
    """Create settings without Gemini configuration."""
    return EchoCattackleSettings(
        gemini_api_key="", gemini_model=test_model_name, mcp_server_port=test_port, log_level="INFO"
    )


# Mock client fixtures
@pytest.fixture
def mock_gemini_client():
    """Create a mock Gemini client for testing."""
    mock_client = MagicMock(spec=GeminiClient)

    # Mock the async generate_content method
    async def mock_generate_content(prompt):
        return "This is a test joke about the topic!"

    mock_client.generate_content = mock_generate_content
    return mock_client


# Cattackle instance fixtures
@pytest.fixture
def cattackle_with_gemini(mock_gemini_client):
    """Create cattackle instance with mocked Gemini client."""
    return EchoCattackle(gemini_client=mock_gemini_client)


@pytest.fixture
def cattackle_without_gemini():
    """Create cattackle instance without Gemini client."""
    return EchoCattackle(gemini_client=None)


# Test data fixtures
@pytest.fixture
def sample_text():
    """Sample text for testing."""
    return "hello world"


@pytest.fixture
def sample_accumulated_params():
    """Sample accumulated parameters for testing."""
    return ["param1", "param2", "param3"]


@pytest.fixture
def sample_joke_topic():
    """Sample topic for joke generation."""
    return "cats"
