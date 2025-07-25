import json
import os
import sys

import pytest

# Add the cattackle src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from server import echo, joke, ping  # noqa


@pytest.mark.asyncio
async def test_echo_command_with_text():
    """Tests that the echo command returns the text in JSON format."""
    text = "hello world"
    message = {"chat": {"id": 123}}
    result = await echo(text, message)

    # Parse the JSON response
    parsed = json.loads(result)
    assert parsed["data"] == "hello world"
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
