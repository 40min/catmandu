import contextlib
import logging
import sys
from collections.abc import AsyncIterator

import click
import mcp.types as types
import uvicorn
from dotenv import load_dotenv
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from notion.clients.notion_client import NotionClientWrapper
from notion.config.settings import NotionCattackleSettings, configure_logging, validate_environment
from notion.config.user_config import get_all_user_configs
from notion.core.cattackle import NotionCattackle
from notion.handlers.health import handle_health_check
from notion.handlers.mcp_handlers import handle_tool_call
from notion.handlers.tools import get_tool_definitions
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.types import Receive, Scope, Send

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger("notion-cattackle")


def create_mcp_server(cattackle: NotionCattackle) -> Server:
    """
    Create and configure the MCP server with tool handlers.

    Args:
        cattackle: The NotionCattackle instance to use for handling tools

    Returns:
        Configured MCP Server instance
    """
    app = Server("notion-cattackle")

    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.ContentBlock]:
        result = await handle_tool_call(cattackle, name, arguments)
        return result

    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        return get_tool_definitions()

    return app


def create_starlette_app(mcp_server: Server, cattackle: NotionCattackle, json_response: bool = False) -> Starlette:
    """
    Create the Starlette ASGI application with MCP server integration.

    Args:
        mcp_server: The configured MCP server
        json_response: Whether to use JSON responses instead of SSE streams

    Returns:
        Configured Starlette application
    """
    # Create the session manager with stateless mode
    session_manager = StreamableHTTPSessionManager(
        app=mcp_server,
        event_store=None,
        json_response=json_response,
        stateless=True,
    )

    async def handle_streamable_http(scope: Scope, receive: Receive, send: Send) -> None:
        await session_manager.handle_request(scope, receive, send)

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        """Context manager for session manager and persistent client instances."""
        async with session_manager.run():
            logger.info("Notion cattackle MCP server started with StreamableHTTP!")

            # Initialize persistent NotionClientWrapper instances for each user
            # This ensures cache persistence across requests
            user_configs = get_all_user_configs()
            client_instances = {}

            for username, config in user_configs.items():
                token = config.get("token")
                if token:
                    client_instances[username] = NotionClientWrapper(token)
                    logger.info("Initialized persistent Notion client", username=username)

            # Store client instances in the cattackle for reuse
            cattackle._client_instances = client_instances
            logger.info("Initialized persistent Notion clients", client_count=len(client_instances))

            try:
                yield
            finally:
                logger.info("Notion cattackle MCP server shutting down...")
                # Clean up client instances
                if hasattr(cattackle, "_client_instances"):
                    del cattackle._client_instances

    # Create an ASGI application using the transport
    return Starlette(
        debug=True,
        routes=[
            Mount("/mcp/", app=handle_streamable_http),
            Route("/health", endpoint=handle_health_check, methods=["GET"]),
        ],
        lifespan=lifespan,
    )


def run_server(settings: NotionCattackleSettings, json_response: bool = False) -> None:
    """
    Run the notion cattackle server with the given settings.

    Args:
        settings: Application settings
        json_response: Whether to use JSON responses instead of SSE streams
    """
    # Configure logging
    configure_logging(settings)

    # Validate environment and log configuration status
    if not validate_environment():
        logger.error("Environment validation failed, exiting")
        sys.exit(1)

    # Initialize cattackle instance
    cattackle = NotionCattackle()

    # Create MCP server
    mcp_server = create_mcp_server(cattackle)

    # Create Starlette app
    starlette_app = create_starlette_app(mcp_server, cattackle, json_response)

    # Run the server
    uvicorn.run(starlette_app, host=settings.host, port=settings.port)


@click.command()
@click.option("--port", default=8002, help="Port to listen on for HTTP (overrides port in settings)")
@click.option(
    "--log-level",
    default="INFO",
    help="Logging level (overrides LOG_LEVEL env var)",
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
    """Main CLI entry point for the notion cattackle server."""
    # Load settings from environment
    settings = NotionCattackleSettings()

    # Override with command line arguments if provided
    if port is not None:
        settings.port = port
    if log_level is not None:
        settings.log_level = log_level.upper()

    # Run the server
    run_server(settings, json_response)
    return 0


if __name__ == "__main__":
    sys.exit(main())
