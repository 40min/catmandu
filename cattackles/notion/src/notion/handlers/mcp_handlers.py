import json
from typing import Any, Dict

import mcp.types as types
import structlog
from notion.core.cattackle import NotionCattackle

logger = structlog.get_logger(__name__)


async def handle_tool_call(cattackle: NotionCattackle, name: str, arguments: dict) -> list[types.ContentBlock]:
    """
    Handle MCP tool calls by routing to appropriate cattackle methods.

    This function processes incoming MCP tool calls and routes them to the
    appropriate NotionCattackle methods. It handles the note command
    and formats responses according to the MCP protocol.

    Args:
        cattackle: The NotionCattackle instance
        name: Tool name
        arguments: Tool arguments containing text, username, and optional accumulated_params

    Returns:
        List of content blocks for MCP response with proper JSON formatting

    Raises:
        ValueError: If tool name is unknown

    Requirements: 1.1, 1.4, 4.1, 4.2, 4.3
    """
    logger.info("Processing request of type CallToolRequest", tool_name=name, arguments=arguments)

    try:
        # Route to appropriate method based on tool name
        match name:
            case "note":
                response_data = await _handle_note(cattackle, arguments)
            case _:
                raise ValueError(f"Unknown tool: {name}")

        # Format successful response with proper JSON structure
        response_json = {"data": response_data, "error": ""}
        response_text = json.dumps(response_json, ensure_ascii=False)

        logger.info(
            "Tool call completed successfully",
            tool_name=name,
            response_length=len(response_data),
            response_json=response_text,
        )

        return [
            types.TextContent(
                type="text",
                text=response_text,
            )
        ]

    except ValueError as e:
        # Handle validation errors with specific error messages
        error_message = str(e)
        response_json = {"data": "", "error": error_message}
        response_text = json.dumps(response_json, ensure_ascii=False)

        logger.warning(
            "Tool call validation error",
            tool_name=name,
            error=error_message,
            arguments=arguments,
            response_json=response_text,
        )

        return [
            types.TextContent(
                type="text",
                text=response_text,
            )
        ]

    except Exception as e:
        # Format error response with proper JSON structure for unexpected errors
        error_message = "An unexpected error occurred. Please try again later."
        response_json = {"data": "", "error": error_message}
        response_text = json.dumps(response_json, ensure_ascii=False)

        logger.error(
            "Tool call failed with unexpected error",
            tool_name=name,
            error=str(e),
            error_type=type(e).__name__,
            arguments=arguments,
            response_json=response_text,
        )

        return [
            types.TextContent(
                type="text",
                text=response_text,
            )
        ]


async def _handle_note(cattackle: NotionCattackle, arguments: Dict[str, Any]) -> str:
    """
    Handle the note command by extracting parameters and calling the core logic.

    Args:
        cattackle: The NotionCattackle instance
        arguments: Tool arguments containing text, username, and optional accumulated_params

    Returns:
        Response message from the cattackle

    Raises:
        ValueError: If required parameters are missing

    Requirements: 1.1, 1.4
    """
    logger.debug("Received note command arguments", arguments=arguments)

    # Extract required parameters
    text = arguments.get("text", "")
    username = arguments.get("extra", {}).get("username", "")
    accumulated_params = arguments.get("accumulated_params", [])

    logger.debug(
        "Extracted parameters",
        text_length=len(text),
        username=username,
        accumulated_params_count=len(accumulated_params) if accumulated_params else 0,
    )

    # Validate required parameters
    if not username:
        logger.warning("Missing username in note command", arguments=arguments)
        raise ValueError("Username is required for note command")

    if not text and not accumulated_params:
        logger.warning("Missing content in note command", arguments=arguments)
        raise ValueError("Either text or accumulated_params must be provided")

    # Additional validation for username format
    if not isinstance(username, str) or len(username.strip()) == 0:
        logger.warning("Invalid username format in note command", username=username, username_type=type(username))
        raise ValueError("Username must be a non-empty string")

    logger.debug(
        "Processing note command with validated parameters",
        username=username,
        text_length=len(text),
        accumulated_params_count=len(accumulated_params) if accumulated_params else 0,
    )

    # Call the core cattackle logic
    response = await cattackle.save_to_notion(
        username=username, message_content=text, accumulated_params=accumulated_params if accumulated_params else None
    )

    logger.debug("Note command completed", username=username, response_length=len(response))

    return response
