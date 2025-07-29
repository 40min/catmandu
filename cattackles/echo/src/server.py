import contextlib
import json
import logging
import os
import sys
from collections.abc import AsyncIterator

import click
import google.generativeai as genai
import mcp.types as types
import uvicorn
from dotenv import load_dotenv
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.types import Receive, Scope, Send

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger("echo-cattackle")

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


# Tool functions for backward compatibility with tests
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


def mcp_tool_wrapper(tool_func):
    """Decorator that converts tool functions to MCP format."""

    async def wrapper(arguments: dict) -> list[types.ContentBlock]:
        text = arguments.get("text", "")
        accumulated_params = arguments.get("accumulated_params", [])

        response = await tool_func(text, accumulated_params)

        return [
            types.TextContent(
                type="text",
                text=response,
            )
        ]

    return wrapper


@mcp_tool_wrapper
def echo_tool(text: str, accumulated_params: list) -> str:
    """HTTP MCP wrapper for echo function."""
    return echo(text, accumulated_params)


@mcp_tool_wrapper
def ping_tool(text: str, accumulated_params: list) -> str:
    """HTTP MCP wrapper for ping function."""
    return ping(text, accumulated_params)


@mcp_tool_wrapper
def joke_tool(text: str, accumulated_params: list) -> str:
    """HTTP MCP wrapper for joke function."""
    return joke(text, accumulated_params)


@click.command()
@click.option("--port", default=8001, help="Port to listen on for HTTP")
@click.option(
    "--log-level",
    default="INFO",
    help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
)
@click.option(
    "--json-response",
    is_flag=True,
    default=False,
    help="Enable JSON responses instead of SSE streams",
)
def main(
    port: int,
    log_level: str,
    json_response: bool,
) -> int:
    # Configure logging based on environment variable
    log_level_env = os.environ.get("LOG_LEVEL", log_level)
    logging.basicConfig(
        level=getattr(logging, log_level_env.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        force=True,
    )

    # Create MCP server
    app = Server("echo-cattackle")

    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.ContentBlock]:
        if name == "echo":
            return await echo_tool(arguments)
        elif name == "ping":
            return await ping_tool(arguments)
        elif name == "joke":
            return await joke_tool(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")

    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="echo",
                description=(
                    "Echoes back the given text. Supports both immediate parameters and accumulated messages. "
                    "Usage: /echo_echo <your text> or send messages first then /echo_echo"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "The text to echo (immediate parameter)",
                        },
                        "accumulated_params": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of accumulated messages (optional)",
                        },
                    },
                    "required": ["text"],
                },
            ),
            types.Tool(
                name="ping",
                description="Returns a simple pong response with parameter information.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Optional text (logged but ignored)",
                        },
                        "accumulated_params": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of accumulated messages (logged but ignored)",
                        },
                    },
                    "required": ["text"],
                },
            ),
            types.Tool(
                name="joke",
                description=(
                    "Generates a funny anekdot about the given topic. Supports accumulated parameters. "
                    "Usage: /echo_joke <your topic> or send a message first then /echo_joke"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "The topic or text to create a joke about (immediate parameter)",
                        },
                        "accumulated_params": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of accumulated messages (optional)",
                        },
                    },
                    "required": ["text"],
                },
            ),
        ]

    # Create the session manager with stateless mode
    session_manager = StreamableHTTPSessionManager(
        app=app,
        event_store=None,
        json_response=json_response,
        stateless=True,
    )

    async def handle_streamable_http(scope: Scope, receive: Receive, send: Send) -> None:
        await session_manager.handle_request(scope, receive, send)

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        """Context manager for session manager."""
        async with session_manager.run():
            logger.info("Echo cattackle MCP server started with StreamableHTTP!")
            try:
                yield
            finally:
                logger.info("Echo cattackle MCP server shutting down...")

    # Create an ASGI application using the transport
    starlette_app = Starlette(
        debug=True,
        routes=[
            Mount("/mcp", app=handle_streamable_http),
        ],
        lifespan=lifespan,
    )

    uvicorn.run(starlette_app, host="127.0.0.1", port=port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
