import json
import logging
import os

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
async def echo(text: str, accumulated_params: list = None) -> str:
    """
    Echoes back the text from the payload, with support for accumulated parameters.
    Returns exactly the same text as entered, joining accumulated messages with semicolon.

    Args:
        text: The text to echo (immediate parameter)
        accumulated_params: List of accumulated messages (optional)

    Returns:
        JSON string with data and error fields
    """
    logger.info(f"Received echo request with text: '{text}', accumulated_params: {accumulated_params}")

    # Handle accumulated parameters vs immediate parameters
    if accumulated_params and len(accumulated_params) > 0:
        # Use accumulated parameters joined with semicolon
        logger.info(f"Using accumulated parameters: {accumulated_params}")
        data = "; ".join(accumulated_params)
    elif text.strip():
        # Use immediate parameter
        logger.info(f"Using immediate parameter: '{text}'")
        data = text
    else:
        # No parameters provided
        data = (
            "Please provide some text to echo. Usage: /echo_echo <your text> or send messages first then use /echo_echo"
        )

    response = json.dumps({"data": data, "error": None})

    logger.info(f"Sending echo response: {response}")
    return response


@mcp.tool("ping")
async def ping(text: str, accumulated_params: list = None) -> str:
    """
    Returns a simple pong response with information about parameters received.

    Args:
        text: Optional text (logged but ignored)
        accumulated_params: List of accumulated messages (logged but ignored)

    Returns:
        JSON string with pong response
    """
    logger.info(f"Received ping request with text: '{text}', accumulated_params: {accumulated_params}")

    # Show parameter information in response for demonstration
    param_info = ""
    if accumulated_params and len(accumulated_params) > 0:
        param_info = f" (received {len(accumulated_params)} accumulated params)"
    elif text.strip():
        param_info = f" (received immediate param: '{text}')"

    response = json.dumps({"data": f"pong{param_info}", "error": None})

    logger.info(f"Sending ping response: {response}")
    return response


@mcp.tool("joke")
async def joke(text: str, accumulated_params: list = None) -> str:
    """
    Generates a funny anekdot (short joke) about the provided text using LLM.
    Supports both immediate parameters and accumulated parameters.

    Args:
        text: The topic or text to create a joke about (immediate parameter)
        accumulated_params: List of accumulated messages (optional)

    Returns:
        JSON string with joke or error
    """
    logger.info(f"Received joke request with text: '{text}', accumulated_params: {accumulated_params}")

    # Determine the topic for the joke
    topic = None
    if accumulated_params and len(accumulated_params) > 0:
        # Use first accumulated parameter as topic
        topic = accumulated_params[0].strip()
        logger.info(f"Using accumulated parameter as joke topic: '{topic}'")
    elif text.strip():
        # Use immediate parameter as topic
        topic = text.strip()
        logger.info(f"Using immediate parameter as joke topic: '{topic}'")

    # Check input first
    if not topic:
        return json.dumps(
            {
                "data": "",
                "error": (
                    "Please provide some text to create a joke about. "
                    "Usage: /echo_joke <your topic> or send a message first then use /echo_joke"
                ),
            }
        )

    # Then check if API is available
    if not model:
        return json.dumps(
            {"data": "", "error": "Joke feature is not available. Please configure GEMINI_API_KEY in .env file."}
        )

    try:
        # Create a prompt for generating a short, funny anekdot
        prompt = f"""Create a short, funny anekdot (joke) about: {topic}

The anekdot should be:
- Short (1-3 sentences)
- Funny and witty
- Family-friendly
- In the style of a classic anekdot or dad joke
- Related to the topic: {topic}

Just return the joke, no additional text."""

        # Generate the joke using Gemini
        response_obj = model.generate_content(prompt)
        joke_text = response_obj.text.strip()

        response = json.dumps({"data": joke_text, "error": None})
        logger.info(f"Generated joke successfully for topic: {topic}")
        return response

    except Exception as e:
        logger.error(f"Error generating joke: {e}")
        return json.dumps({"data": "", "error": f"Failed to generate joke: {str(e)}"})


if __name__ == "__main__":
    logger.info("Starting Echo cattackle MCP server")
    mcp.run()
