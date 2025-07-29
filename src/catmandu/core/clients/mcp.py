"""
MCP (Model Context Protocol) client.

Provides a thin wrapper around the MCP Python SDK for protocol communication.
Focuses on transport and session management only.
"""

import asyncio
import os
from contextlib import AsyncExitStack
from typing import Any, Dict, Tuple

import structlog
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.websocket import websocket_client

from catmandu.core.errors import CattackleExecutionError
from catmandu.core.models import (
    HttpTransportConfig,
    StdioTransportConfig,
    WebSocketTransportConfig,
)


class McpClient:
    """
    MCP protocol client for communicating with cattackles.

    This is a stateless wrapper around the MCP Python SDK that handles
    protocol communication and session management. Business logic should
    be implemented in services that use this client.
    """

    def __init__(self):
        self.log = structlog.get_logger(self.__class__.__name__)

    async def create_session(self, transport_config) -> Tuple[AsyncExitStack, ClientSession]:
        """
        Create an MCP session based on transport configuration.

        Args:
            transport_config: Transport configuration (STDIO, WebSocket, or HTTP)

        Returns:
            Tuple of (AsyncExitStack, ClientSession) for proper cleanup

        Raises:
            CattackleExecutionError: If transport type is unsupported or session creation fails
        """
        if isinstance(transport_config, StdioTransportConfig):
            return await self._create_stdio_session(transport_config)
        elif isinstance(transport_config, WebSocketTransportConfig):
            return await self._create_websocket_session(transport_config)
        elif isinstance(transport_config, HttpTransportConfig):
            return await self._create_http_session(transport_config)
        else:
            raise CattackleExecutionError(f"Unsupported transport type: {transport_config.type}")

    async def call_tool(self, session: ClientSession, tool_name: str, arguments: Dict[str, Any], timeout: float = 30.0):
        """
        Call a tool on an MCP session with timeout.

        Args:
            session: Active MCP client session
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
            timeout: Timeout in seconds

        Returns:
            Tool response from MCP session

        Raises:
            asyncio.TimeoutError: If the call times out
            Exception: If the tool call fails
        """
        return await asyncio.wait_for(session.call_tool(tool_name, arguments), timeout=timeout)

    async def check_session_health(self, session: ClientSession) -> bool:
        """
        Check if an MCP session is still healthy and usable.

        Args:
            session: The session to check

        Returns:
            True if the session is healthy, False otherwise
        """
        try:
            await session.list_tools()
            return True
        except Exception as e:
            self.log.debug("Session health check failed", error=str(e))
            return False

    async def _create_stdio_session(self, config: StdioTransportConfig) -> Tuple[AsyncExitStack, ClientSession]:
        """Create a STDIO-based MCP session."""
        self.log.debug("Creating STDIO MCP session", command=config.command)

        # Prepare environment variables
        env = os.environ.copy()
        if config.env:
            env.update(config.env)

        server_params = StdioServerParameters(command=config.command, args=config.args or [], env=env, cwd=config.cwd)

        try:
            exit_stack = AsyncExitStack()
            reader, writer = await exit_stack.enter_async_context(stdio_client(server_params))
            session = await exit_stack.enter_async_context(ClientSession(reader, writer))
            await session.initialize()
            return exit_stack, session

        except Exception as e:
            self.log.error("Failed to create STDIO session", command=config.command, error=str(e))
            if "exit_stack" in locals():
                await exit_stack.aclose()
            raise CattackleExecutionError(f"Failed to create STDIO session: {e}") from e

    async def _create_websocket_session(self, config: WebSocketTransportConfig) -> Tuple[AsyncExitStack, ClientSession]:
        """Create a WebSocket-based MCP session."""
        self.log.debug("Creating WebSocket MCP session", url=config.url)

        try:
            exit_stack = AsyncExitStack()
            reader, writer = await exit_stack.enter_async_context(websocket_client(config.url))
            session = await exit_stack.enter_async_context(ClientSession(reader, writer))
            await session.initialize()
            return exit_stack, session

        except Exception as e:
            self.log.error("Failed to create WebSocket session", url=config.url, error=str(e))
            if "exit_stack" in locals():
                await exit_stack.aclose()
            raise CattackleExecutionError(f"Failed to create WebSocket session: {e}") from e

    async def _create_http_session(self, config: HttpTransportConfig) -> Tuple[AsyncExitStack, ClientSession]:
        """Create an HTTP-based MCP session."""
        self.log.debug("Creating HTTP MCP session", url=config.url)

        headers = config.headers or {}

        try:
            exit_stack = AsyncExitStack()
            reader, writer, get_session_id = await exit_stack.enter_async_context(
                streamablehttp_client(config.url, headers=headers)
            )
            session = await exit_stack.enter_async_context(ClientSession(reader, writer))
            await session.initialize()
            session.get_session_id = get_session_id
            return exit_stack, session

        except Exception as e:
            self.log.error("Failed to create HTTP session", url=config.url, error=str(e))
            if "exit_stack" in locals():
                await exit_stack.aclose()
            raise CattackleExecutionError(f"Failed to create HTTP session: {e}") from e
