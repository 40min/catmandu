import asyncio
import os
from contextlib import AsyncExitStack
from typing import Dict, Tuple

import structlog
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.websocket import websocket_client

from catmandu.core.errors import CattackleExecutionError
from catmandu.core.models import (
    CattackleConfig,
    CattackleResponse,
    HttpTransportConfig,
    StdioTransportConfig,
    WebSocketTransportConfig,
)


class McpClientManager:
    """
    Manages MCP client sessions for communicating with cattackles.

    This service abstracts the communication with cattackle processes using
    the official Model Context Protocol Python SDK. It supports multiple
    transport protocols (STDIO, WebSocket, HTTP) and provides session
    management with proper context manager usage for resource cleanup.
    """

    def __init__(self):
        self.log = structlog.get_logger(self.__class__.__name__)
        # Store exit stacks and sessions together for proper cleanup
        self._active_contexts: Dict[str, Tuple[AsyncExitStack, ClientSession]] = {}

    async def call(self, cattackle_config: CattackleConfig, command: str, payload: dict) -> CattackleResponse:
        """
        Execute a command on a cattackle with the given payload.

        Args:
            cattackle_config: Configuration for the cattackle
            command: Command name to execute
            payload: Data to send to the cattackle

        Returns:
            CattackleResponse with the result data

        Raises:
            CattackleExecutionError: If the execution fails or times out
        """
        cattackle_name = cattackle_config.cattackle.name
        transport_config = cattackle_config.cattackle.mcp.transport
        timeout = cattackle_config.cattackle.mcp.timeout
        max_retries = cattackle_config.cattackle.mcp.max_retries

        self.log.info(
            "Calling cattackle",
            cattackle=cattackle_name,
            command=command,
            transport_type=transport_config.type,
        )

        # Implement retry logic
        retry_count = 0
        last_error = None

        while retry_count <= max_retries:
            try:
                session = await self._get_or_create_session(cattackle_config)

                # Call the tool with timeout
                response = await asyncio.wait_for(session.call_tool(command, {"payload": payload}), timeout=timeout)

                # Extract the response data from the first content item
                if response.content and len(response.content) > 0:
                    return CattackleResponse(data=response.content[0].text)
                return CattackleResponse(data={})

            except asyncio.TimeoutError as e:
                last_error = e
                self.log.warning(
                    "Cattackle execution timed out, retrying",
                    cattackle=cattackle_name,
                    command=command,
                    timeout=timeout,
                    retry=retry_count + 1,
                    max_retries=max_retries,
                )
            except Exception as e:
                last_error = e
                self.log.warning(
                    "Cattackle execution failed, retrying",
                    cattackle=cattackle_name,
                    command=command,
                    error=str(e),
                    retry=retry_count + 1,
                    max_retries=max_retries,
                )

            # Close the failed session and remove it from active sessions
            await self.close_session(cattackle_name)

            # Increment retry counter
            retry_count += 1

            # Wait before retrying with exponential backoff
            if retry_count <= max_retries:
                backoff_time = 0.5 * (2**retry_count)  # Exponential backoff
                await asyncio.sleep(backoff_time)

        # If we get here, all retries failed
        error_type = "timeout" if isinstance(last_error, asyncio.TimeoutError) else "execution error"
        self.log.error(
            f"Cattackle {error_type} after all retries",
            cattackle=cattackle_name,
            command=command,
            max_retries=max_retries,
            error=str(last_error),
        )

        if isinstance(last_error, asyncio.TimeoutError):
            raise CattackleExecutionError(
                f"Cattackle '{cattackle_name}' timed out after {timeout}s (retries: {max_retries})"
            ) from last_error
        else:
            raise CattackleExecutionError(
                f"Failed to execute cattackle '{cattackle_name}': {last_error}"
            ) from last_error

    async def _get_or_create_session(self, cattackle_config: CattackleConfig) -> ClientSession:
        """
        Get existing session or create a new one for the cattackle.

        Args:
            cattackle_config: Configuration for the cattackle

        Returns:
            ClientSession: An initialized MCP client session

        Raises:
            CattackleExecutionError: If the transport type is unsupported
        """
        cattackle_name = cattackle_config.cattackle.name

        # Check if we have an active session
        if cattackle_name in self._active_contexts:
            exit_stack, session = self._active_contexts[cattackle_name]
            # Check if session is still valid
            if await self._check_session_health(session):
                return session
            else:
                # Session is not healthy, close it and create a new one
                await self.close_session(cattackle_name)

        # Create new session based on transport type
        transport_config = cattackle_config.cattackle.mcp.transport

        if isinstance(transport_config, StdioTransportConfig):
            exit_stack, session = await self._create_stdio_session(transport_config)
        elif isinstance(transport_config, WebSocketTransportConfig):
            exit_stack, session = await self._create_websocket_session(transport_config)
        elif isinstance(transport_config, HttpTransportConfig):
            exit_stack, session = await self._create_http_session(transport_config)
        else:
            raise CattackleExecutionError(f"Unsupported transport type: {transport_config.type}")

        self._active_contexts[cattackle_name] = (exit_stack, session)
        return session

    async def _check_session_health(self, session: ClientSession) -> bool:
        """
        Check if a session is still healthy and usable.

        Args:
            session: The session to check

        Returns:
            bool: True if the session is healthy, False otherwise
        """
        try:
            # Try to list tools as a health check
            await session.list_tools()
            return True
        except Exception as e:
            self.log.debug("Session health check failed", error=str(e))
            return False

    async def _create_stdio_session(self, config: StdioTransportConfig) -> Tuple[AsyncExitStack, ClientSession]:
        """
        Create a stdio-based MCP session using proper context management.

        Args:
            config: STDIO transport configuration

        Returns:
            Tuple of (AsyncExitStack, ClientSession): Exit stack for cleanup and initialized session
        """
        self.log.info("Creating STDIO MCP session", command=config.command)

        # Prepare environment variables
        env = os.environ.copy()  # Start with current environment
        if config.env:
            env.update(config.env)  # Add cattackle-specific variables

        # Create server parameters
        server_params = StdioServerParameters(command=config.command, args=config.args or [], env=env, cwd=config.cwd)

        try:
            # Use AsyncExitStack to manage context managers
            # Note: LIFO cleanup order ensures session is closed before transport
            exit_stack = AsyncExitStack()

            # Enter the stdio_client context manager first
            reader, writer = await exit_stack.enter_async_context(stdio_client(server_params))

            # Enter the ClientSession context manager second (will be closed first due to LIFO)
            session = await exit_stack.enter_async_context(ClientSession(reader, writer))
            await session.initialize()

            return exit_stack, session

        except Exception as e:
            self.log.error("Failed to create STDIO session", command=config.command, error=str(e))
            # Clean up the exit stack if session creation failed
            if "exit_stack" in locals():
                await exit_stack.aclose()
            raise CattackleExecutionError(f"Failed to create STDIO session: {e}") from e

    async def _create_websocket_session(self, config: WebSocketTransportConfig) -> Tuple[AsyncExitStack, ClientSession]:
        """
        Create a WebSocket-based MCP session using proper context management.

        Args:
            config: WebSocket transport configuration

        Returns:
            Tuple of (AsyncExitStack, ClientSession): Exit stack for cleanup and initialized session
        """
        self.log.info("Creating WebSocket MCP session", url=config.url)

        # Prepare headers
        headers = config.headers or {}

        try:
            # Use AsyncExitStack to manage context managers
            # Note: LIFO cleanup order ensures session is closed before transport
            exit_stack = AsyncExitStack()

            # Enter the websocket_client context manager first
            reader, writer = await exit_stack.enter_async_context(websocket_client(config.url))

            # Enter the ClientSession context manager second (will be closed first due to LIFO)
            session = await exit_stack.enter_async_context(ClientSession(reader, writer))
            await session.initialize()

            return exit_stack, session

        except Exception as e:
            self.log.error("Failed to create WebSocket session", url=config.url, error=str(e))
            # Clean up the exit stack if session creation failed
            if "exit_stack" in locals():
                await exit_stack.aclose()
            raise CattackleExecutionError(f"Failed to create WebSocket session: {e}") from e

    async def _create_http_session(self, config: HttpTransportConfig) -> Tuple[AsyncExitStack, ClientSession]:
        """
        Create an HTTP-based MCP session using proper context management.

        Args:
            config: HTTP transport configuration

        Returns:
            Tuple of (AsyncExitStack, ClientSession): Exit stack for cleanup and initialized session
        """
        self.log.info("Creating HTTP MCP session", url=config.url)

        # Prepare headers
        headers = config.headers or {}

        try:
            # Use AsyncExitStack to manage context managers
            # Note: LIFO cleanup order ensures session is closed before transport
            exit_stack = AsyncExitStack()

            # Enter the streamablehttp_client context manager first
            reader, writer, get_session_id = await exit_stack.enter_async_context(
                streamablehttp_client(config.url, headers=headers)
            )

            # Enter the ClientSession context manager second (will be closed first due to LIFO)
            session = await exit_stack.enter_async_context(ClientSession(reader, writer))
            await session.initialize()

            # Store the session ID callback for potential future use
            session.get_session_id = get_session_id

            return exit_stack, session

        except Exception as e:
            self.log.error("Failed to create HTTP session", url=config.url, error=str(e))
            # Clean up the exit stack if session creation failed
            if "exit_stack" in locals():
                await exit_stack.aclose()
            raise CattackleExecutionError(f"Failed to create HTTP session: {e}") from e

    async def close_session(self, cattackle_name: str):
        """
        Close and remove a session for a specific cattackle.

        Args:
            cattackle_name: Name of the cattackle whose session to close
        """
        if cattackle_name in self._active_contexts:
            exit_stack, session = self._active_contexts.pop(cattackle_name)
            try:
                # Properly close the context manager stack
                await exit_stack.aclose()
                self.log.debug("Closed session context", cattackle=cattackle_name)
            except Exception as e:
                self.log.warning("Error closing session context", cattackle=cattackle_name, error=str(e))

    async def close_all_sessions(self):
        """Close all active sessions."""
        for cattackle_name in list(self._active_contexts.keys()):
            await self.close_session(cattackle_name)
