import pytest

from cattackles.echo.src.server import echo, ping


@pytest.mark.asyncio
async def test_echo_command():
    """Tests that the echo command returns the input payload with metadata."""
    payload = {"message": "hello world"}
    result = await echo(payload)

    # Check that the original payload is preserved
    assert result["message"] == "hello world"

    # Check that metadata is added
    assert "metadata" in result
    assert "timestamp" in result["metadata"]
    assert "size" in result["metadata"]
    assert result["metadata"]["size"] > 0


@pytest.mark.asyncio
async def test_ping_command():
    """Tests that the ping command returns a pong response."""
    payload = {"test": "data"}
    result = await ping(payload)

    # Check the response structure
    assert result["response"] == "pong"
    assert "timestamp" in result
    assert result["payload"] == payload
