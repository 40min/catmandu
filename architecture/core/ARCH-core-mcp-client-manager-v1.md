---
id: ARCH-core-mcp-client-manager
title: "Core: MCP Client Manager"
type: service
layer: infrastructure
owner: '@catmandu-devs'
version: v1
status: planned
created: 2025-07-16
updated: 2025-07-16
tags: [core, mcp, rpc]
depends_on: [ARCH-cattackle-spec]
referenced_by: []
---
## Context
The MCP Client Manager is a dedicated service that abstracts all communication with external cattackle processes. It provides a clean, internal API for the rest of the core system to interact with cattackles, hiding the complexities of the underlying MCP (Model Context Protocol) library.

## Structure
This service will be implemented as a class that encapsulates the `mcp-client` library. It will have a primary method, `call_cattackle`, which takes a target cattackle's details and a request payload. It is responsible for establishing a connection, sending the request, awaiting the response, and handling any communication errors.

Key file: `catmandu.services.mcp_client`

## Behavior
When the Message Router needs to execute a command on a cattackle, it calls the `call_cattackle` method on the MCP Client Manager. The manager uses the cattackle's configuration (retrieved from the Cattackle Registry) to determine how to connect (e.g., stdio, websocket). It then executes the remote procedure call and returns the `CattackleResponse` to the Message Router. This component is responsible for connection management and error handling related to the RPC calls.

## Evolution
### Planned
- **v1:** Initial implementation with simple, on-demand connections.
- Future optimizations could include connection pooling for websocket/HTTP-based cattackles to improve performance and reduce latency.