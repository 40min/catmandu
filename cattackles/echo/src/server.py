import logging
import os
import time
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
async def echo(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Echoes back the payload.

    Args:
        payload: The data to echo back

    Returns:
        The same payload with an added timestamp
    """
    logger.info(f"Received echo request with payload: {payload}")

    # Get max payload size from settings
    max_size = 1024  # Default value

    # Check payload size if needed
    payload_size = len(str(payload))
    if payload_size > max_size:
        logger.warning(f"Payload size ({payload_size}) exceeds maximum ({max_size})")

    # Add metadata to response
    result = {**payload, "metadata": {"timestamp": time.time(), "size": payload_size}}

    logger.info(f"Sending echo response: {result}")
    return result


@mcp.tool("ping")
async def ping(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns a pong response with timestamp.

    Args:
        payload: Optional parameters

    Returns:
        A pong response with timestamp
    """
    logger.info(f"Received ping request with payload: {payload}")

    result = {"response": "pong", "timestamp": time.time(), "payload": payload}

    logger.info(f"Sending ping response: {result}")
    return result


if __name__ == "__main__":
    logger.info("Starting Echo cattackle MCP server")
    mcp.run()
