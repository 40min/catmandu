---
id: ARCH-cattackle-spec
title: "Specification: Cattackle Module"
type: specification
layer: integration
owner: '@catmandu-devs'
version: v1
status: planned
created: 2025-07-16
updated: 2025-07-16
tags: [cattackle, mcp, spec, toml]
depends_on: []
referenced_by: []
---
## Context
A "cattackle" is an independent, pluggable module that provides specific features to the Catmandu bot. This specification defines the contract that a cattackle must adhere to in order to be discovered and used by the Catmandu Core system. This allows for language-agnostic development of features.

## Structure
A cattackle must be a self-contained directory that includes its source code, dependencies, and a manifest file.

```
cattackles/
└── my-cattackle/
    ├── cattackle.toml     # Manifest file (required)
    ├── src/               # Cattackle source code
    ├── requirements.txt   # or package.json, etc.
    └── README.md
```

### cattackle.toml
This TOML file is the manifest that the `CattackleRegistry` uses for discovery.
```toml
[cattackle]
name = "my-cattackle"
version = "1.0.0"
description = "A brief description of the cattackle."

[cattackle.commands]
mycommand = { description = "Description of mycommand" }

[cattackle.mcp]
transport = "stdio" # "stdio" or "websocket" or "http"
```

### Core Models
Communication between the core and cattackles uses standardized Pydantic models for requests and responses, such as `CattackleRequest` and `CattackleResponse`. These define the data contract for all interactions.

## Behavior
Each cattackle must run an MCP (Model Context Protocol) server, such as `FastMCP`. The Catmandu Core's `MCPClientManager` will connect to this server based on the `[cattackle.mcp]` configuration in the `cattackle.toml` file to execute commands.