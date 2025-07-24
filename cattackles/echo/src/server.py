import json
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
        JSON string with data and error fields
    """
    logger.info(f"Received echo request with text: {text}, message: {message}")

    # If no text provided, return a helpful message
    if not text.strip():
        data = "Please provide some text to echo. Usage: /echo_echo <your text>"
    else:
        data = text

    response = json.dumps({"data": data, "error": None})

    logger.info(f"Sending echo response: {response}")
    return response


@mcp.tool("ping")
async def ping(text: str, message: Dict[str, Any]) -> str:
    """
    Returns a simple pong response.

    Args:
        text: Optional text (ignored)
        message: The Telegram message metadata (ignored)

    Returns:
        JSON string with pong response
    """
    logger.info(f"Received ping request with text: {text}, message: {message}")

    response = json.dumps({"data": "pong", "error": None})

    logger.info(f"Sending ping response: {response}")
    return response


@mcp.tool("divide")
async def divide(text: str, message: Dict[str, Any]) -> str:
    """
    Divides two numbers from the text input.

    Args:
        text: Two numbers separated by space (e.g., "10 2")
        message: The Telegram message metadata

    Returns:
        JSON string with result or error
    """
    logger.info(f"Received divide request with text: {text}, message: {message}")

    try:
        # Parse the input
        parts = text.strip().split()
        if len(parts) != 2:
            return json.dumps(
                {"data": "", "error": "Please provide exactly two numbers separated by space. Usage: /echo_divide 10 2"}
            )

        try:
            num1 = float(parts[0])
            num2 = float(parts[1])
        except ValueError:
            return json.dumps({"data": "", "error": "Invalid numbers provided. Please use valid numeric values."})

        # Check for division by zero
        if num2 == 0:
            return json.dumps({"data": "", "error": "Cannot divide by zero!"})

        # Perform division
        result = num1 / num2
        response = json.dumps({"data": f"{num1} ÷ {num2} = {result}", "error": None})

        logger.info(f"Sending divide response: {response}")
        return response

    except Exception as e:
        logger.error(f"Unexpected error in divide: {e}")
        return json.dumps({"data": "", "error": f"An unexpected error occurred: {str(e)}"})


if __name__ == "__main__":
    logger.info("Starting Echo cattackle MCP server")
    mcp.run()
