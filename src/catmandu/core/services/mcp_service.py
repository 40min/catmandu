"""
MCP service for managing cattackle communication.

Handles business logic for cattackle execution including session management,
retry logic, and response processing.
"""

import asyncio
from contextlib import AsyncExitStack
from typing import Dict, Tuple

import structlog
from mcp import ClientSession

from catmandu.core.clients.mcp import McpClient
from catmandu.core.errors import CattackleExecutionError
from catmandu.core.models import CattackleConfig, CattackleResponse


class McpService:
    """
    Service for managing MCP communication with cattackles.

    This service orchestrates cattackle execution including session management,
    retry logic, error handling, and response processing. It uses McpClient
    for the actual protocol communication.
    """

    def __init__(self, mcp_client: McpClient):
        self.log = structlog.get_logger(self.__class__.__name__)
        self.mcp_client = mcp_client
        # Store exit stacks and sessions together for proper cleanup
        self._active_contexts: Dict[str, Tuple[AsyncExitStack, ClientSession]] = {}

    async def execute_cattackle(
        self, cattackle_config: CattackleConfig, command: str, payload: dict
    ) -> CattackleResponse:
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
            "Executing cattackle",
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
                response = await self.mcp_client.call_tool(session, command, {"payload": payload}, timeout)

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
                backoff_time = 0.5 * (2**retry_count)
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
        """Get existing session or create a new one for the cattackle."""
        cattackle_name = cattackle_config.cattackle.name

        # Check if we have an active session
        if cattackle_name in self._active_contexts:
            exit_stack, session = self._active_contexts[cattackle_name]
            # Check if session is still valid
            if await self.mcp_client.check_session_health(session):
                return session
            else:
                # Session is not healthy, close it and create a new one
                await self.close_session(cattackle_name)

        # Create new session
        transport_config = cattackle_config.cattackle.mcp.transport
        exit_stack, session = await self.mcp_client.create_session(transport_config)
        self._active_contexts[cattackle_name] = (exit_stack, session)
        return session

    async def close_session(self, cattackle_name: str):
        """
        Close and remove a session for a specific cattackle.

        Args:
            cattackle_name: Name of the cattackle whose session to close
        """
        if cattackle_name in self._active_contexts:
            exit_stack, session = self._active_contexts.pop(cattackle_name)
            try:
                await exit_stack.aclose()
                self.log.debug("Closed session context", cattackle=cattackle_name)
            except Exception as e:
                self.log.warning("Error closing session context", cattackle=cattackle_name, error=str(e))

    async def close_all_sessions(self):
        """Close all active sessions."""
        for cattackle_name in list(self._active_contexts.keys()):
            await self.close_session(cattackle_name)
