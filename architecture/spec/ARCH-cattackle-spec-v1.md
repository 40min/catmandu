---
layer: integration
owner: '@catmandu-devs'
version: v1
status: current
created: 2025-07-16
updated: 2025-07-21
tags: [cattackle, mcp, spec, toml, transport]
depends_on: []
referenced_by: [ARCH-core-mcp-client-manager]
---
# ARCH-cattackle-spec-v1

## Overview
This document specifies the contract and expected behavior for cattackles within the Catmandu framework. It defines the structure of cattackle configurations, the interface for cattackle implementations, and the communication protocols they adhere to using the Model Context Protocol (MCP).

## Cattackle Configuration (TOML)
Cattackles are configured using TOML files located at `cattackles/{name}/cattackle.toml`. The specification defines the required and optional fields within these files.

### Required Fields
```toml
[cattackle]
name = "cattackle-name"           # Unique identifier for the cattackle
version = "0.1.0"                 # Semantic version of the cattackle
description = "Brief description" # Human-readable description

[cattackle.commands]
command_name = { description = "Command description" }

[cattackle.mcp]
timeout = 30.0      # Optional: Command timeout in seconds (default: 30.0)
max_retries = 3     # Optional: Max retry attempts (default: 3)

[cattackle.mcp.transport]
type = "stdio"  # Transport type: "stdio", "websocket", or "http"
```

### MCP Transport Configuration

#### STDIO Transport
For process-based cattackles that communicate via stdin/stdout:
```toml
[cattackle.mcp]
timeout = 30.0      # Optional: Command timeout in seconds (default: 30.0)
max_retries = 3     # Optional: Max retry attempts (default: 3)

[cattackle.mcp.transport]
type = "stdio"
command = "python"                           # Executable command
args = ["-m", "cattackles.echo.src.server"] # Command arguments
env = { "PYTHONPATH" = "." }                # Optional: Environment variables
cwd = "/path/to/working/directory"          # Optional: Working directory
```

#### WebSocket Transport (Planned)
For real-time bidirectional communication:
```toml
[cattackle.mcp.transport]
type = "websocket"
url = "ws://localhost:8080/mcp"
headers = { "Authorization" = "Bearer token" }  # Optional: Custom headers
```

#### HTTP Transport (Planned)
For RESTful communication:
```toml
[cattackle.mcp.transport]
type = "http"
url = "http://localhost:8080/mcp"
headers = { "Authorization" = "Bearer token" }  # Optional: Custom headers
```

### Optional Fields
- `tags`: List of tags for categorization
- `dependencies`: List of other cattackles this cattackle depends on
- `settings`: Configuration settings specific to the cattackle

### Complete Example
```toml
[cattackle]
name = "echo"
version = "0.1.0"
description = "A simple cattackle that echoes back the payload."
tags = ["utility", "testing"]

[cattackle.commands]
echo = { description = "Echoes back the given payload." }
ping = { description = "Returns a pong response." }

[cattackle.mcp]
timeout = 30.0
max_retries = 3

[cattackle.mcp.transport]
type = "stdio"
command = "python"
args = ["-m", "cattackles.echo.src.server"]
env = { "PYTHONPATH" = ".", "LOG_LEVEL" = "INFO" }

[cattackle.settings]
max_payload_size = 1024
enable_logging = true
```

## Cattackle Implementation Interface
Cattackle implementations must provide an MCP server that exposes tools corresponding to their configured commands.

### MCP Server Requirements
1. **Tool Registration**: Each command must be registered as an MCP tool
2. **Parameter Handling**: Tools must accept a `payload` parameter containing the request data
3. **Response Format**: Tools must return structured data that can be serialized
4. **Error Handling**: Proper error responses for invalid requests

### Example Implementation (Python with FastMCP)
```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Echo", description="Echo cattackle", version="0.1.0")

@mcp.tool("echo")
async def echo(payload: dict) -> dict:
    """Echoes back the payload."""
    return payload

@mcp.tool("ping")
async def ping(payload: dict) -> dict:
    """Returns a pong response."""
    return {"response": "pong", "timestamp": time.time()}

if __name__ == "__main__":
    mcp.run()
```

## Language Agnostic Support
Cattackles can be implemented in any language that supports MCP:

- **Python**: Using `fastmcp` or `mcp` libraries
- **JavaScript/TypeScript**: Using `@modelcontextprotocol/sdk`
- **Rust**: Using MCP Rust implementations
- **Go**: Using MCP Go implementations
- **Other Languages**: Any language with MCP server capabilities

## Directory Structure
```
cattackles/{name}/
├── cattackle.toml          # Configuration file (required)
├── requirements.txt        # Dependencies (Python cattackles)
├── package.json           # Dependencies (Node.js cattackles)
├── src/                   # Source code directory
│   ├── server.py         # MCP server implementation
│   └── ...               # Additional source files
├── tests/                # Test files (optional)
└── README.md             # Documentation (recommended)
```

## Evolution
### Current (v1)
- ✅ TOML-based configuration with enhanced MCP transport settings
- ✅ STDIO transport support with full configuration options
- ✅ Command registration and validation
- ✅ Language-agnostic cattackle support

### Planned (v2)
- WebSocket and HTTP transport implementations
- Schema validation for cattackle settings
- Dependency management between cattackles
- Versioning and compatibility checks
- Health check endpoints for long-running cattackles
