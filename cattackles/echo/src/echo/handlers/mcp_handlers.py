import mcp.types as types
from echo.core.cattackle import EchoCattackle


async def handle_tool_call(cattackle: EchoCattackle, name: str, arguments: dict) -> list[types.ContentBlock]:
    """
    Handle MCP tool calls by routing to appropriate cattackle methods.

    Args:
        cattackle: The EchoCattackle instance
        name: Tool name
        arguments: Tool arguments

    Returns:
        List of content blocks for MCP response

    Raises:
        ValueError: If tool name is unknown
    """
    # Extract common parameters
    text = arguments.get("text", "")
    accumulated_params = arguments.get("accumulated_params", [])

    # Route to appropriate method and get response
    match name:
        case "echo":
            response = await cattackle.echo(text, accumulated_params)
        case "ping":
            response = await cattackle.ping(text, accumulated_params)
        case "joke":
            response = await cattackle.joke(text, accumulated_params)
        case _:
            raise ValueError(f"Unknown tool: {name}")

    # Format response for MCP
    return [
        types.TextContent(
            type="text",
            text=response,
        )
    ]
