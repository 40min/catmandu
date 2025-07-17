from fastmcp import FastMCP

mcp = FastMCP()


@mcp.tool("echo")
async def echo(payload: dict) -> dict:
    """Echoes back the payload."""
    return payload


if __name__ == "__main__":
    mcp.run()
