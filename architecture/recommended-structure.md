# Recommended Package Structure

```
src/catmandu/core/
├── clients/                 # External API clients (stateless wrappers)
│   ├── __init__.py
│   ├── telegram.py         # TelegramClient (HTTP API wrapper)
│   └── mcp.py             # McpClient (protocol wrapper)
├── services/               # Business logic services (stateful)
│   ├── __init__.py
│   ├── message_router.py   # MessageRouter (routing logic)
│   ├── poller.py          # TelegramPoller (polling orchestration)
│   └── registry.py        # CattackleRegistry (cattackle management)
├── repositories/           # Data access layer (if needed later)
│   └── __init__.py
├── models.py              # Domain models
├── config.py              # Configuration
└── errors.py              # Custom exceptions
```

## Key Distinctions

### Clients (External Interface Layer)
- Thin wrappers around external APIs
- Stateless or minimal state
- Focus on protocol/transport concerns
- Easy to mock in tests
- Examples: HTTP clients, database drivers, message queue clients

### Services (Business Logic Layer)
- Orchestrate business workflows
- Maintain application state
- Use clients to interact with external systems
- Contain domain logic and rules
- Examples: user management, message processing, workflow orchestration

### Repositories (Data Access Layer)
- Abstract data storage/retrieval
- Can use clients internally
- Domain-focused interface
- Examples: user repository, message repository
