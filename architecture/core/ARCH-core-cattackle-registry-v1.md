---
id: ARCH-core-cattackle-registry
title: "Core: Cattackle Registry"
type: service
layer: application
owner: '@catmandu-devs'
version: v1
status: planned
created: 2025-07-16
updated: 2025-07-16
tags: [core, registry, discovery]
depends_on: [ARCH-cattackle-spec]
referenced_by: []
---
## Context
The Cattackle Registry is a singleton service responsible for the dynamic discovery and registration of cattackle modules. It provides a central, in-memory cache of available cattackles, allowing the core system to route commands without manual configuration or restarts for new modules.

## Structure
The registry works by scanning a predefined directory (e.g., `cattackles/`) at startup. For each subdirectory found, it looks for and parses a `cattackle.toml` manifest file. The parsed configurations, which include command definitions and MCP connection details, are stored in an in-memory dictionary or list.

Key files:
- `catmandu.services.registry`: The Python module containing the registry implementation.
- `cattackle.toml`: The manifest file that each cattackle must provide.

## Behavior
The registry is initialized during the application's startup sequence. It performs an initial scan of the cattackles directory. It also exposes a method to be called by an administrative endpoint (e.g., `/admin/reload`) to trigger a re-scan of the directory, allowing for hot-reloading of cattackle configurations. Other services, like the Message Router, query the registry to find the appropriate cattackle for a given command.

## Evolution
### Planned
- **v1:** Initial implementation with directory scanning and in-memory storage.
- Caching of registry data to a persistent store like Redis could be a future optimization.