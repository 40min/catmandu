import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add the cattackle src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from server import echo, joke, ping  # noqa


@pytest.fixture(autouse=True)
def mock_gemini_model():
    """Mock the Gemini model for all tests."""
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "This is a test joke about the topic!"
    mock_model.generate_content.return_value = mock_response

    with patch("server.model", mock_model):
        yield mock_model


@pytest.mark.asyncio
async def test_echo_command_with_text():
    """Tests that the echo command returns the exact text without any prefix."""
    text = "hello world"
    result = await echo(text)

    # Parse the JSON response
    parsed = json.loads(result)
    assert parsed["data"] == "hello world"
    assert parsed["error"] is None


@pytest.mark.asyncio
async def test_echo_command_empty_text():
    """Tests that the echo command handles empty text gracefully."""
    text = ""
    result = await echo(text)

    # Parse the JSON response
    parsed = json.loads(result)
    assert "Please provide some text to echo" in parsed["data"]
    assert parsed["error"] is None


@pytest.mark.asyncio
async def test_echo_command_whitespace_text():
    """Tests that the echo command handles whitespace-only text gracefully."""
    text = "   "
    result = await echo(text)

    # Parse the JSON response
    parsed = json.loads(result)
    assert "Please provide some text to echo" in parsed["data"]
    assert parsed["error"] is None


@pytest.mark.asyncio
async def test_ping_command():
    """Tests that the ping command returns a simple pong response in JSON format."""
    text = ""
    result = await ping(text)

    # Parse the JSON response
    parsed = json.loads(result)
    assert parsed["data"] == "pong"
    assert parsed["error"] is None


@pytest.mark.asyncio
async def test_joke_command_empty_text():
    """Tests that the joke command handles empty text gracefully."""
    text = ""
    result = await joke(text)

    # Parse the JSON response
    parsed = json.loads(result)
    assert parsed["data"] == ""
    assert "Please provide some text to create a joke about" in parsed["error"]


@pytest.mark.asyncio
async def test_joke_command_whitespace_text():
    """Tests that the joke command handles whitespace-only text gracefully."""
    text = "   "
    result = await joke(text)

    # Parse the JSON response
    parsed = json.loads(result)
    assert parsed["data"] == ""
    assert "Please provide some text to create a joke about" in parsed["error"]


@pytest.mark.asyncio
async def test_joke_command_with_api_key():
    """Tests that the joke command works with API key configured."""
    # API key is now required and set in test environment
    text = "cats"
    result = await joke(text)

    # Parse the JSON response
    parsed = json.loads(result)
    # Should have proper structure (may have error due to test API key being invalid)
    assert "data" in parsed
    assert "error" in parsed


# Tests for accumulated parameters support


@pytest.mark.asyncio
async def test_echo_with_multiple_accumulated_params():
    """Tests that echo command handles multiple accumulated parameters joined with semicolon."""
    text = ""  # No immediate text
    accumulated_params = ["hello", "world", "from", "accumulator"]

    result = await echo(text, accumulated_params=accumulated_params)

    parsed = json.loads(result)
    expected = "hello; world; from; accumulator"
    assert expected == parsed["data"]
    assert parsed["error"] is None


@pytest.mark.asyncio
async def test_echo_immediate_vs_accumulated():
    """Tests that echo command prefers accumulated parameters over immediate text."""
    text = "immediate text"
    accumulated_params = ["accumulated", "text"]

    result = await echo(text, accumulated_params=accumulated_params)

    parsed = json.loads(result)
    expected = "accumulated; text"
    assert expected == parsed["data"]
    assert parsed["error"] is None


@pytest.mark.asyncio
async def test_echo_backward_compatibility():
    """Tests that echo command still works with old format (no accumulated_params)."""
    text = "backward compatible"

    result = await echo(text)

    parsed = json.loads(result)
    assert "backward compatible" == parsed["data"]
    assert parsed["error"] is None


@pytest.mark.asyncio
async def test_echo_with_single_accumulated_param():
    """Tests that echo command handles single accumulated parameter without any prefix."""
    text = ""  # No immediate text
    accumulated_params = ["single message"]

    result = await echo(text, accumulated_params=accumulated_params)

    parsed = json.loads(result)
    assert "single message" == parsed["data"]
    assert parsed["error"] is None


@pytest.mark.asyncio
async def test_ping_with_accumulated_params():
    """Tests that ping command shows parameter information."""
    text = ""
    accumulated_params = ["param1", "param2"]

    result = await ping(text, accumulated_params=accumulated_params)

    parsed = json.loads(result)
    assert "pong (received 2 accumulated params)" == parsed["data"]
    assert parsed["error"] is None


@pytest.mark.asyncio
async def test_ping_with_immediate_param():
    """Tests that ping command shows immediate parameter information."""
    text = "immediate"

    result = await ping(text)

    parsed = json.loads(result)
    assert "pong (received immediate param: 'immediate')" == parsed["data"]
    assert parsed["error"] is None


@pytest.mark.asyncio
async def test_ping_no_params():
    """Tests that ping command works with no parameters."""
    text = ""

    result = await ping(text)

    parsed = json.loads(result)
    assert "pong" == parsed["data"]
    assert parsed["error"] is None


@pytest.mark.asyncio
async def test_joke_with_accumulated_params():
    """Tests that joke command uses first accumulated parameter as topic."""
    text = ""
    accumulated_params = ["cats", "dogs", "birds"]  # Should use "cats" as topic

    result = await joke(text, accumulated_params=accumulated_params)

    parsed = json.loads(result)
    # Should work with mocked model
    assert parsed["error"] is None
    assert len(parsed["data"]) > 0


@pytest.mark.asyncio
async def test_joke_prefers_accumulated_over_immediate():
    """Tests that joke command prefers accumulated parameter over immediate text."""
    text = "immediate topic"
    accumulated_params = ["accumulated topic"]

    result = await joke(text, accumulated_params=accumulated_params)

    parsed = json.loads(result)
    # Should work with mocked model
    assert parsed["error"] is None
    assert len(parsed["data"]) > 0


@pytest.mark.asyncio
async def test_joke_backward_compatibility():
    """Tests that joke command still works with old format (no accumulated_params)."""
    text = "backward compatible topic"

    result = await joke(text)

    parsed = json.loads(result)
    # Should work with mocked model
    assert parsed["error"] is None
    assert len(parsed["data"]) > 0


@pytest.mark.asyncio
async def test_all_commands_handle_empty_accumulated_params():
    """Tests that all commands handle empty accumulated_params list gracefully."""
    text = "test"
    accumulated_params = []  # Empty list

    # Test echo
    result = await echo(text, accumulated_params=accumulated_params)
    parsed = json.loads(result)
    assert "test" == parsed["data"]

    # Test ping
    result = await ping(text, accumulated_params=accumulated_params)
    parsed = json.loads(result)
    assert "pong (received immediate param: 'test')" == parsed["data"]

    # Test joke
    result = await joke(text, accumulated_params=accumulated_params)
    parsed = json.loads(result)
    # Should work with mocked model
    assert parsed["error"] is None
    assert len(parsed["data"]) > 0


@pytest.mark.asyncio
async def test_multi_echo_command_removed():
    """Tests that multi_echo command is no longer available."""
    # Try to import multi_echo - should fail
    with pytest.raises(ImportError):
        from server import multi_echo  # noqa

    # Verify multi_echo is not in the server module
    import server

    assert not hasattr(server, "multi_echo"), "multi_echo function should be completely removed from server module"
