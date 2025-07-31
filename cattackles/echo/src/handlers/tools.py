import mcp.types as types


def get_tool_definitions() -> list[types.Tool]:
    """Get the list of MCP tool definitions for the echo cattackle."""
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
