import logging
import os
from typing import Any, Dict

from mcp.server.fastmcp import FastMCP

# Configure logging based on environment variable
log_level = os.environ.get("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("echo-cattackle")

# Create FastMCP server
mcp = FastMCP("Echo", description="Echo cattackle", version="0.1.0")


@mcp.tool("echo")
async def echo(text: str, message: Dict[str, Any]) -> str:
    """
    Echoes back the text from the payload.

    Args:
        text: The text to echo
        message: The Telegram message metadata

    Returns:
        The text to echo back to the user
    """
    logger.info(f"Received echo request with text: {text}, message: {message}")

    # If no text provided, return a helpful message
    if not text.strip():
        result = "Please provide some text to echo. Usage: /echo_echo <your text>"
    else:
        result = text

    logger.info(f"Sending echo response: {result}")
    return result


@mcp.tool("ping")
async def ping(text: str, message: Dict[str, Any]) -> str:
    """
    Returns a simple pong response.

    Args:
        text: Optional text (ignored)
        message: The Telegram message metadata (ignored)

    Returns:
        A pong response
    """
    logger.info(f"Received ping request with text: {text}, message: {message}")

    result = "pong"

    logger.info(f"Sending ping response: {result}")
    return result


if __name__ == "__main__":
    logger.info("Starting Echo cattackle MCP server")
    mcp.run()
