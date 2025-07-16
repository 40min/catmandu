---
id: ARCH-core-message-router
title: "Core: Message Router"
type: service
layer: application
owner: '@catmandu-devs'
version: v1
status: planned
created: 2025-07-16
updated: 2025-07-16
tags: [core, routing]
depends_on:
  - ARCH-core-cattackle-registry
  - ARCH-core-mcp-client-manager
referenced_by: []
---
## Context
The Message Router contains the primary business logic for processing an incoming Telegram update. Its role is to receive an update from the Telegram Poller, determine the user's intent, and orchestrate the interaction with the appropriate cattackle module.

## Structure
The Message Router is a service that exposes a main method, such as `process_update`. This method contains the logic to:
1.  Parse the Telegram `Update` object, extracting the message and command.
2.  Query the `CattackleRegistry` to find which cattackle is responsible for the parsed command.
3.  Construct a standardized `CattackleRequest` Pydantic model.
4.  Invoke the `MCPClientManager` to send the request to the target cattackle.
5.  Receive the `CattackleResponse` and format a reply to be sent back to Telegram.

## Behavior
The router acts as a controller in the system's request/response flow. It receives raw data, enriches it, delegates the core work to a cattackle via the MCP manager, and then handles the result. It is responsible for error handling, such as when a command is not found in the registry or a cattackle call fails.