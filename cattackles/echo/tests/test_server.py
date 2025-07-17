import pytest
from fastmcp import Client

from cattackles.echo.src.server import mcp

# from mcp.types import TextContent


@pytest.mark.asyncio
async def test_echo_command():
    """Tests that the echo command returns the input payload."""
    async with Client(mcp) as client:
        payload = {"message": "hello world"}
        result = await client.call_tool("echo", {"message": "hello world"})
        # assert isinstance(result[0], TextContent)
        # assert result[0].text == "3"

        assert result == payload
