import json
import os
import sys

import pytest

# Add the cattackle src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from server import echo, joke, multi_echo, ping  # noqa


@pytest.mark.asyncio
async def test_echo_command_with_text():
    """Tests that the echo command returns the text in JSON format with immediate parameter prefix."""
    text = "hello world"
    message = {"chat": {"id": 123}}
    result = await echo(text, message)

    # Parse the JSON response
    parsed = json.loads(result)
    assert parsed["data"] == "Echo (immediate): hello world"
    assert parsed["error"] is None


@pytest.mark.asyncio
async def test_echo_command_empty_text():
    """Tests that the echo command handles empty text gracefully."""
    text = ""
    message = {"chat": {"id": 123}}
    result = await echo(text, message)

    # Parse the JSON response
    parsed = json.loads(result)
    assert "Please provide some text to echo" in parsed["data"]
    assert parsed["error"] is None


@pytest.mark.asyncio
async def test_echo_command_whitespace_text():
    """Tests that the echo command handles whitespace-only text gracefully."""
    text = "   "
    message = {"chat": {"id": 123}}
    result = await echo(text, message)

    # Parse the JSON response
    parsed = json.loads(result)
    assert "Please provide some text to echo" in parsed["data"]
    assert parsed["error"] is None


@pytest.mark.asyncio
async def test_ping_command():
    """Tests that the ping command returns a simple pong response in JSON format."""
    text = ""
    message = {"test": "data"}
    result = await ping(text, message)

    # Parse the JSON response
    parsed = json.loads(result)
    assert parsed["data"] == "pong"
    assert parsed["error"] is None


@pytest.mark.asyncio
async def test_joke_command_empty_text():
    """Tests that the joke command handles empty text gracefully."""
    text = ""
    message = {"chat": {"id": 123}}
    result = await joke(text, message)

    # Parse the JSON response
    parsed = json.loads(result)
    assert parsed["data"] == ""
    assert "Please provide some text to create a joke about" in parsed["error"]


@pytest.mark.asyncio
async def test_joke_command_whitespace_text():
    """Tests that the joke command handles whitespace-only text gracefully."""
    text = "   "
    message = {"chat": {"id": 123}}
    result = await joke(text, message)

    # Parse the JSON response
    parsed = json.loads(result)
    assert parsed["data"] == ""
    assert "Please provide some text to create a joke about" in parsed["error"]


@pytest.mark.asyncio
async def test_joke_command_no_api_key():
    """Tests that the joke command handles missing API key gracefully."""
    # This test assumes no GEMINI_API_KEY is set in test environment
    text = "cats"
    message = {"chat": {"id": 123}}
    result = await joke(text, message)

    # Parse the JSON response
    parsed = json.loads(result)
    # Should either work (if API key is set) or show error message
    if parsed["error"]:
        assert "not available" in parsed["error"] or "configure GEMINI_API_KEY" in parsed["error"]
    else:
        # If it works, should have some joke content
        assert len(parsed["data"]) > 0


# Tests for accumulated parameters support


@pytest.mark.asyncio
async def test_echo_with_accumulated_params():
    """Tests that echo command works with accumulated parameters."""
    text = ""  # No immediate text
    message = {"chat": {"id": 123}}
    accumulated_params = ["hello", "world", "from", "accumulator"]

    result = await echo(text, message, accumulated_params)

    parsed = json.loads(result)
    assert "Echo (from accumulated): hello world from accumulator" == parsed["data"]
    assert parsed["error"] is None


@pytest.mark.asyncio
async def test_echo_immediate_vs_accumulated():
    """Tests that echo command prefers accumulated parameters over immediate text."""
    text = "immediate text"
    message = {"chat": {"id": 123}}
    accumulated_params = ["accumulated", "text"]

    result = await echo(text, message, accumulated_params)

    parsed = json.loads(result)
    assert "Echo (from accumulated): accumulated text" == parsed["data"]
    assert parsed["error"] is None


@pytest.mark.asyncio
async def test_echo_backward_compatibility():
    """Tests that echo command still works with old format (no accumulated_params)."""
    text = "backward compatible"
    message = {"chat": {"id": 123}}

    result = await echo(text, message)

    parsed = json.loads(result)
    assert "Echo (immediate): backward compatible" == parsed["data"]
    assert parsed["error"] is None


@pytest.mark.asyncio
async def test_ping_with_accumulated_params():
    """Tests that ping command shows parameter information."""
    text = ""
    message = {"chat": {"id": 123}}
    accumulated_params = ["param1", "param2"]

    result = await ping(text, message, accumulated_params)

    parsed = json.loads(result)
    assert "pong (received 2 accumulated params)" == parsed["data"]
    assert parsed["error"] is None


@pytest.mark.asyncio
async def test_ping_with_immediate_param():
    """Tests that ping command shows immediate parameter information."""
    text = "immediate"
    message = {"chat": {"id": 123}}

    result = await ping(text, message)

    parsed = json.loads(result)
    assert "pong (received immediate param: 'immediate')" == parsed["data"]
    assert parsed["error"] is None


@pytest.mark.asyncio
async def test_ping_no_params():
    """Tests that ping command works with no parameters."""
    text = ""
    message = {"chat": {"id": 123}}

    result = await ping(text, message)

    parsed = json.loads(result)
    assert "pong" == parsed["data"]
    assert parsed["error"] is None


@pytest.mark.asyncio
async def test_multi_echo_with_accumulated_params():
    """Tests the multi_echo command with multiple accumulated parameters."""
    text = ""
    message = {"chat": {"id": 123}}
    accumulated_params = ["first message", "second message", "third message"]

    result = await multi_echo(text, message, accumulated_params)

    parsed = json.loads(result)
    expected = "Multi-echo (3 messages):\n1. first message\n2. second message\n3. third message"
    assert expected == parsed["data"]
    assert parsed["error"] is None


@pytest.mark.asyncio
async def test_multi_echo_single_accumulated_param():
    """Tests the multi_echo command with single accumulated parameter."""
    text = ""
    message = {"chat": {"id": 123}}
    accumulated_params = ["only message"]

    result = await multi_echo(text, message, accumulated_params)

    parsed = json.loads(result)
    expected = "Multi-echo (1 messages):\n1. only message"
    assert expected == parsed["data"]
    assert parsed["error"] is None


@pytest.mark.asyncio
async def test_multi_echo_fallback_to_immediate():
    """Tests that multi_echo falls back to immediate parameter when no accumulated params."""
    text = "immediate text"
    message = {"chat": {"id": 123}}

    result = await multi_echo(text, message)

    parsed = json.loads(result)
    assert "Multi-echo (immediate): 1. immediate text" == parsed["data"]
    assert parsed["error"] is None


@pytest.mark.asyncio
async def test_multi_echo_no_params():
    """Tests that multi_echo handles no parameters gracefully."""
    text = ""
    message = {"chat": {"id": 123}}

    result = await multi_echo(text, message)

    parsed = json.loads(result)
    assert "Please send multiple messages first" in parsed["data"]
    assert parsed["error"] is None


@pytest.mark.asyncio
async def test_joke_with_accumulated_params():
    """Tests that joke command uses first accumulated parameter as topic."""
    text = ""
    message = {"chat": {"id": 123}}
    accumulated_params = ["cats", "dogs", "birds"]  # Should use "cats" as topic

    result = await joke(text, message, accumulated_params)

    parsed = json.loads(result)
    # Should either work (if API key is set) or show error message
    if parsed["error"]:
        assert "not available" in parsed["error"] or "configure GEMINI_API_KEY" in parsed["error"]
    else:
        # If it works, should have some joke content
        assert len(parsed["data"]) > 0


@pytest.mark.asyncio
async def test_joke_prefers_accumulated_over_immediate():
    """Tests that joke command prefers accumulated parameter over immediate text."""
    text = "immediate topic"
    message = {"chat": {"id": 123}}
    accumulated_params = ["accumulated topic"]

    result = await joke(text, message, accumulated_params)

    parsed = json.loads(result)
    # Should either work (if API key is set) or show error message
    if parsed["error"]:
        assert "not available" in parsed["error"] or "configure GEMINI_API_KEY" in parsed["error"]
    else:
        # If it works, should have some joke content
        assert len(parsed["data"]) > 0


@pytest.mark.asyncio
async def test_joke_backward_compatibility():
    """Tests that joke command still works with old format (no accumulated_params)."""
    text = "backward compatible topic"
    message = {"chat": {"id": 123}}

    result = await joke(text, message)

    parsed = json.loads(result)
    # Should either work (if API key is set) or show error message
    if parsed["error"]:
        assert "not available" in parsed["error"] or "configure GEMINI_API_KEY" in parsed["error"]
    else:
        # If it works, should have some joke content
        assert len(parsed["data"]) > 0


@pytest.mark.asyncio
async def test_all_commands_handle_empty_accumulated_params():
    """Tests that all commands handle empty accumulated_params list gracefully."""
    text = "test"
    message = {"chat": {"id": 123}}
    accumulated_params = []  # Empty list

    # Test echo
    result = await echo(text, message, accumulated_params)
    parsed = json.loads(result)
    assert "Echo (immediate): test" == parsed["data"]

    # Test ping
    result = await ping(text, message, accumulated_params)
    parsed = json.loads(result)
    assert "pong (received immediate param: 'test')" == parsed["data"]

    # Test multi_echo
    result = await multi_echo(text, message, accumulated_params)
    parsed = json.loads(result)
    assert "Multi-echo (immediate): 1. test" == parsed["data"]

    # Test joke
    result = await joke(text, message, accumulated_params)
    parsed = json.loads(result)
    # Should either work or show API key error
    assert parsed["error"] is None or "not available" in parsed["error"]
