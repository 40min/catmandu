"""
MCP service for managing cattackle communication.

Handles business logic for cattackle execution including session management,
retry logic, and response processing.
"""

import asyncio
import json
from contextlib import AsyncExitStack
from typing import Dict, Tuple

import structlog
from mcp import ClientSession
from pydantic import ValidationError

from catmandu.core.clients.mcp import McpClient
from catmandu.core.errors import CattackleExecutionError, CattackleResponseError, CattackleValidationError
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
        self, cattackle_config: CattackleConfig, command: str, payload: dict, user_info: dict
    ) -> CattackleResponse:
        """
        Execute a command on a cattackle with the given payload.

        Args:
            cattackle_config: Configuration for the cattackle
            command: Command name to execute
            payload: Data to send to the cattackle
            user_info: User information to include for cattackles that need it

        Returns:
            CattackleResponse with the result data

        Raises:
            CattackleExecutionError: If the execution fails or times out
        """
        cattackle_name = cattackle_config.name
        transport_config = cattackle_config.mcp.transport
        timeout = cattackle_config.mcp.timeout
        max_retries = cattackle_config.mcp.max_retries

        self.log.info(
            "Executing cattackle",
            cattackle=cattackle_name,
            command=command,
            transport_type=transport_config.type,
            payload=payload,
            user_info=user_info,
        )

        # Implement retry logic
        retry_count = 0
        last_error = None

        while retry_count <= max_retries:
            try:
                session = await self._get_or_create_session(cattackle_config)

                # Enhance payload with extra information for all cattackles
                enhanced_payload = payload.copy()
                # Add extra information that cattackles can use if needed
                enhanced_payload["extra"] = {"username": (user_info or {}).get("username", "undefined")}

                self.log.debug(
                    "Sending to cattackle", cattackle=cattackle_name, command=command, payload=enhanced_payload
                )

                # Call the tool with timeout
                response = await self.mcp_client.call_tool(session, command, enhanced_payload, timeout)

                # Extract the response data from the first content item
                if response.content and len(response.content) > 0:
                    response_text = response.content[0].text

                    # Parse as JSON - all cattackles must return JSON responses
                    try:
                        parsed_response = json.loads(response_text)
                        return CattackleResponse(
                            data=parsed_response.get("data", ""), error=parsed_response.get("error")
                        )
                    except (json.JSONDecodeError, TypeError) as e:
                        self.log.error(
                            "Cattackle returned invalid JSON response",
                            cattackle=cattackle_name,
                            command=command,
                            response=response_text,
                            error=str(e),
                        )
                        # Check if this looks like a validation error (should not be retried)
                        if "validation error" in response_text.lower() or "required property" in response_text.lower():
                            raise CattackleValidationError(
                                f"Cattackle '{cattackle_name}' input validation failed: {response_text}"
                            ) from e
                        else:
                            raise CattackleResponseError(
                                f"Cattackle '{cattackle_name}' returned invalid JSON response: {e}"
                            ) from e

                return CattackleResponse(data="", error="Empty response from cattackle")

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
            except (CattackleValidationError, CattackleResponseError) as e:
                # These errors should not be retried - they indicate permanent issues
                self.log.error(
                    "Cattackle execution failed with non-retryable error",
                    cattackle=cattackle_name,
                    command=command,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise e
            except ValidationError as e:
                # Validation errors are internal and shouldn't be retried
                self.log.error(
                    "Cattackle response validation failed",
                    cattackle=cattackle_name,
                    command=command,
                    error=str(e),
                )
                raise CattackleExecutionError(f"Invalid response format from cattackle '{cattackle_name}': {e}") from e
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
        cattackle_name = cattackle_config.name

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
        transport_config = cattackle_config.mcp.transport
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
