"""
Common test fixtures for the echo cattackle test suite.
These fixtures are available to all test modules.
"""

from unittest.mock import MagicMock

import pytest
from echo.clients.gemini_client import GeminiClient
from echo.clients.openai_client import OpenAIClient
from echo.config import EchoCattackleSettings
from echo.core.cattackle import EchoCattackle


# Common test data fixtures
@pytest.fixture
def test_openai_api_key():
    """Standard test OpenAI API key."""
    return "test-openai-api-key"


@pytest.fixture
def test_gemini_api_key():
    """Standard test Gemini API key."""
    return "test-gemini-api-key"


@pytest.fixture
def test_openai_model():
    """Standard test OpenAI model name."""
    return "gpt-5-nano"


@pytest.fixture
def test_gemini_model():
    """Standard test Gemini model name."""
    return "gemini-pro"


@pytest.fixture
def test_port():
    """Standard test port."""
    return 8001


# Settings fixtures
@pytest.fixture
def settings_with_openai_only(test_openai_api_key, test_openai_model, test_gemini_model, test_port):
    """Create settings with only OpenAI configuration."""
    return EchoCattackleSettings(
        openai_api_key=test_openai_api_key,
        openai_model=test_openai_model,
        gemini_api_key=None,
        gemini_model=test_gemini_model,
        mcp_server_port=test_port,
        log_level="INFO",
    )


@pytest.fixture
def settings_with_gemini_only(test_gemini_api_key, test_openai_model, test_gemini_model, test_port):
    """Create settings with only Gemini configuration."""
    return EchoCattackleSettings(
        openai_api_key=None,
        openai_model=test_openai_model,
        gemini_api_key=test_gemini_api_key,
        gemini_model=test_gemini_model,
        mcp_server_port=test_port,
        log_level="INFO",
    )


@pytest.fixture
def settings_with_both_apis(test_openai_api_key, test_gemini_api_key, test_openai_model, test_gemini_model, test_port):
    """Create settings with both OpenAI and Gemini configuration."""
    return EchoCattackleSettings(
        openai_api_key=test_openai_api_key,
        openai_model=test_openai_model,
        gemini_api_key=test_gemini_api_key,
        gemini_model=test_gemini_model,
        mcp_server_port=test_port,
        log_level="INFO",
    )


@pytest.fixture
def settings_without_apis(test_openai_model, test_gemini_model, test_port):
    """Create settings without any AI API configuration."""
    return EchoCattackleSettings(
        openai_api_key=None,
        openai_model=test_openai_model,
        gemini_api_key=None,
        gemini_model=test_gemini_model,
        mcp_server_port=test_port,
        log_level="INFO",
    )


# Mock client fixtures
@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client for testing."""
    mock_client = MagicMock(spec=OpenAIClient)

    # Mock the async generate_content method
    async def mock_generate_content(prompt):
        return "This is a test OpenAI joke about the topic!"

    mock_client.generate_content = mock_generate_content
    return mock_client


@pytest.fixture
def mock_gemini_client():
    """Create a mock Gemini client for testing."""
    mock_client = MagicMock(spec=GeminiClient)

    # Mock the async generate_content method
    async def mock_generate_content(prompt):
        return "This is a test Gemini joke about the topic!"

    mock_client.generate_content = mock_generate_content
    return mock_client


# Cattackle instance fixtures
@pytest.fixture
def cattackle_with_openai_only(mock_openai_client):
    """Create cattackle instance with only OpenAI client."""
    return EchoCattackle(openai_client=mock_openai_client, gemini_client=None)


@pytest.fixture
def cattackle_with_gemini_only(mock_gemini_client):
    """Create cattackle instance with only Gemini client."""
    return EchoCattackle(openai_client=None, gemini_client=mock_gemini_client)


@pytest.fixture
def cattackle_with_both_clients(mock_openai_client, mock_gemini_client):
    """Create cattackle instance with both OpenAI and Gemini clients."""
    return EchoCattackle(openai_client=mock_openai_client, gemini_client=mock_gemini_client)


@pytest.fixture
def cattackle_without_clients():
    """Create cattackle instance without any AI clients."""
    return EchoCattackle(openai_client=None, gemini_client=None)


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
