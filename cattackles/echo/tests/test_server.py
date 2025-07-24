import pytest

from cattackles.echo.src.server import echo, ping


@pytest.mark.asyncio
async def test_echo_command_with_text():
    """Tests that the echo command returns the text directly."""
    text = "hello world"
    message = {"chat": {"id": 123}}
    result = await echo(text, message)

    # Check that only the text is returned
    assert result == "hello world"


@pytest.mark.asyncio
async def test_echo_command_empty_text():
    """Tests that the echo command handles empty text gracefully."""
    text = ""
    message = {"chat": {"id": 123}}
    result = await echo(text, message)

    # Check that a helpful message is returned
    assert "Please provide some text to echo" in result


@pytest.mark.asyncio
async def test_echo_command_whitespace_text():
    """Tests that the echo command handles whitespace-only text gracefully."""
    text = "   "
    message = {"chat": {"id": 123}}
    result = await echo(text, message)

    # Check that a helpful message is returned
    assert "Please provide some text to echo" in result


@pytest.mark.asyncio
async def test_ping_command():
    """Tests that the ping command returns a simple pong response."""
    text = ""
    message = {"test": "data"}
    result = await ping(text, message)

    # Check the response is just "pong"
    assert result == "pong"
