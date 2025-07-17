from fastmcp import FastMcp

mcp = FastMcp()


@mcp.command()
async def echo(payload: dict) -> dict:
    """Echoes back the payload."""
    return payload


if __name__ == "__main__":
    mcp.run()
