import mcp.types as types


def get_tool_definitions() -> list[types.Tool]:
    """Get the list of MCP tool definitions for the notion cattackle."""
    return [
        types.Tool(
            name="to_notion",
            description=(
                "Save message content to a daily Notion page organized by date. "
                "Supports both immediate parameters and accumulated messages. "
                "Usage: /to_notion <your message> or send messages first then /to_notion"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The message content to save to Notion (immediate parameter)",
                    },
                    "accumulated_params": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of accumulated messages (optional)",
                    },
                    "username": {
                        "type": "string",
                        "description": "Telegram username of the user making the request",
                    },
                },
                "required": ["text", "username"],
            },
        ),
    ]
