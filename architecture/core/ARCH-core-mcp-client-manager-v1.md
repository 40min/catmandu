---
id: ARCH-core-mcp-client-manager
title: "Core: MCP Client Manager"
type: service
layer: infrastructure
owner: '@catmandu-devs'
version: v1
status: implemented
created: 2025-07-16
updated: 2025-07-21
tags: [core, mcp, rpc, transport]
depends_on: [ARCH-cattackle-spec]
referenced_by: []
---
## Context
The MCP Client Manager is a dedicated service that abstracts all communication with external cattackle processes using the official Model Context Protocol Python SDK. It provides a clean, internal API for the rest of the core system to interact with cattackles, supporting multiple transport protocols and advanced connection management.

## Structure
This service is implemented as the `McpClientManager` class that encapsulates the official `mcp` Python SDK. It provides session management, connection pooling, and supports multiple transport types:

- **STDIO Transport**: Process-based communication via stdin/stdout
- **WebSocket Transport**: Real-time bidirectional communication
- **HTTP Transport**: RESTful communication

Key file: `src/catmandu/core/services/mcp_client.py`

## Transport Configuration
Each cattackle defines its transport configuration in `cattackle.toml`:

### STDIO Transport
```toml
[cattackle.mcp.transport]
type = "stdio"
command = "python"
args = ["-m", "cattackles.echo.src.server"]
env = { "PYTHONPATH" = ".", "LOG_LEVEL" = "INFO" }
cwd = "/optional/working/directory"
```

### WebSocket Transport
```toml
[cattackle.mcp.transport]
type = "websocket"
url = "ws://localhost:8080/mcp"
headers = { "Authorization" = "Bearer token" }
```

### HTTP Transport
```toml
[cattackle.mcp.transport]
type = "http"
url = "http://localhost:8080/mcp"
headers = { "Authorization" = "Bearer token" }
```

## Behavior
The MCP Client Manager maintains persistent sessions for each cattackle to improve performance:

1. **Session Management**: Creates and caches ClientSession instances per cattackle
2. **Connection Handling**: Establishes connections based on transport configuration
3. **Error Handling**: Provides comprehensive error handling with retries and timeouts
4. **Resource Management**: Properly closes sessions and cleans up resources
5. **Retry Logic**: Implements exponential backoff for failed calls

### Key Methods
- `call()`: Execute a command on a cattackle with payload and retry logic
- `_get_or_create_session()`: Manage session lifecycle with health checks
- `_check_session_health()`: Verify session is still valid and usable
- `_create_stdio_session()`: Create STDIO-based MCP session
- `_create_websocket_session()`: Create WebSocket-based MCP session
- `_create_http_session()`: Create HTTP-based MCP session
- `close_session()`: Clean up individual cattackle sessions
- `close_all_sessions()`: Shutdown all active sessions

## Configuration Options
Each cattackle can specify MCP-specific settings:

```toml
[cattackle.mcp]
timeout = 30.0        # Command execution timeout in seconds
max_retries = 3       # Maximum retry attempts for failed calls

[cattackle.settings]
max_payload_size = 1024    # Maximum size of payload in bytes
enable_logging = true      # Enable detailed logging for this cattackle
```

## Implementation Details

### Session Management
The MCP Client Manager maintains a dictionary of active sessions keyed by cattackle name. When a call is made to a cattackle, the manager first checks if an active session exists. If not, it creates a new session based on the transport configuration.

### Retry Logic
The manager implements retry logic with exponential backoff for failed calls:
1. If a call fails, the manager will retry up to `max_retries` times
2. Each retry uses exponential backoff to avoid overwhelming the cattackle
3. After all retries are exhausted, the manager raises a `CattackleExecutionError`

### Error Handling
The manager provides comprehensive error handling:
1. Timeouts are handled with configurable timeout values
2. Connection errors are caught and retried
3. Protocol errors are logged and propagated
4. Resource cleanup is performed even in error cases

### Transport Implementations
The manager supports multiple transport types:
1. **STDIO**: Uses `mcp.client.stdio.stdio_client` for process-based communication
2. **WebSocket**: Uses `mcp.client.websocket.websocket_client` for real-time communication
3. **HTTP**: Uses `mcp.client.http.http_client` for RESTful communication

## Evolution
### Current (v1)
- ✅ STDIO transport with official Python SDK
- ✅ WebSocket transport with official Python SDK
- ✅ HTTP transport with official Python SDK
- ✅ Session management and connection pooling
- ✅ Comprehensive error handling and logging
- ✅ Configurable timeouts and retries
- ✅ Retry logic with exponential backoff

### Planned (v2)
- Health checks for long-lived sessions
- Connection keep-alive mechanisms
- Metrics and monitoring integration
- Circuit breaker pattern for failing cattackles
- Graceful degradation for unavailable cattackles
