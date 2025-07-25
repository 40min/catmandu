import json
import logging
import os
from typing import Any, Dict

import google.generativeai as genai
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load environment variables from .env file
load_dotenv()

# Configure logging based on environment variable
log_level = os.environ.get("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True,
)
logger = logging.getLogger("echo-cattackle")

# Create FastMCP server
mcp = FastMCP("Echo", description="Funny echo cattackle with AI joke generation", version="0.1.0")

# Configure Gemini API
gemini_api_key = os.environ.get("GEMINI_API_KEY")
gemini_model = os.environ.get("GEMINI_MODEL")
if gemini_api_key and gemini_model:
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel(gemini_model)
    logger.info("Gemini API configured successfully")
else:
    model = None
    logger.warning("GEMINI_API_KEY not found in environment variables. Joke command will not work.")


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


@mcp.tool("joke")
async def joke(text: str, message: Dict[str, Any]) -> str:
    """
    Generates a funny anekdot (short joke) about the provided text using LLM.

    Args:
        text: The topic or text to create a joke about
        message: The Telegram message metadata

    Returns:
        JSON string with joke or error
    """
    logger.info(f"Received joke request with text: {text}, message: {message}")

    # Check input first
    if not text.strip():
        return json.dumps(
            {"data": "", "error": "Please provide some text to create a joke about. Usage: /echo_joke <your topic>"}
        )

    # Then check if API is available
    if not model:
        return json.dumps(
            {"data": "", "error": "Joke feature is not available. Please configure GEMINI_API_KEY in .env file."}
        )

    try:
        # Create a prompt for generating a short, funny anekdot
        prompt = f"""Create a short, funny anekdot (joke) about: {text.strip()}

The anekdot should be:
- Short (1-3 sentences)
- Funny and witty
- Family-friendly
- In the style of a classic anekdot or dad joke
- Related to the topic: {text.strip()}

Just return the joke, no additional text."""

        # Generate the joke using Gemini
        response_obj = model.generate_content(prompt)
        joke_text = response_obj.text.strip()

        response = json.dumps({"data": joke_text, "error": None})
        logger.info(f"Generated joke successfully for topic: {text}")
        return response

    except Exception as e:
        logger.error(f"Error generating joke: {e}")
        return json.dumps({"data": "", "error": f"Failed to generate joke: {str(e)}"})


if __name__ == "__main__":
    logger.info("Starting Echo cattackle MCP server")
    mcp.run()
