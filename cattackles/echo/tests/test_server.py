import json
import os
import sys

import pytest

# Add the cattackle src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from server import divide, echo, ping  # noqa


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
async def test_divide_command_success():
    """Tests that the divide command works correctly with valid input."""
    text = "10 2"
    message = {"chat": {"id": 123}}
    result = await divide(text, message)

    # Parse the JSON response
    parsed = json.loads(result)
    assert parsed["data"] == "10.0 ÷ 2.0 = 5.0"
    assert parsed["error"] is None


@pytest.mark.asyncio
async def test_divide_command_division_by_zero():
    """Tests that the divide command handles division by zero."""
    text = "10 0"
    message = {"chat": {"id": 123}}
    result = await divide(text, message)

    # Parse the JSON response
    parsed = json.loads(result)
    assert parsed["data"] == ""
    assert parsed["error"] == "Cannot divide by zero!"


@pytest.mark.asyncio
async def test_divide_command_invalid_input():
    """Tests that the divide command handles invalid input."""
    text = "not a number"
    message = {"chat": {"id": 123}}
    result = await divide(text, message)

    # Parse the JSON response
    parsed = json.loads(result)
    assert parsed["data"] == ""
    assert "Please provide exactly two numbers" in parsed["error"]


@pytest.mark.asyncio
async def test_divide_command_invalid_numbers():
    """Tests that the divide command handles non-numeric values."""
    text = "abc def"
    message = {"chat": {"id": 123}}
    result = await divide(text, message)

    # Parse the JSON response
    parsed = json.loads(result)
    assert parsed["data"] == ""
    assert "Invalid numbers provided" in parsed["error"]
