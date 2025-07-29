---
layer: application
owner: '@catmandu-devs'
version: v1
status: current
created: 2025-07-16
updated: 2025-07-16
tags: [core, registry, discovery]
depends_on: [ARCH-cattackle-spec]
referenced_by: []
---
# ARCH-core-cattackle-registry-v1

## Overview
The Cattackle Registry is a core component responsible for discovering, loading, and managing available cattackles within the Catmandu system. It acts as a central hub for cattackle management, ensuring that the system can dynamically adapt to new functionalities.

## Responsibilities
- Discover cattackles by scanning specified directories.
- Load and validate cattackle configurations (e.g., TOML files).
- Provide an interface to access loaded cattackles.
- Manage the lifecycle of cattackle instances.

## Architecture
The registry operates as a singleton service within the core application. Initially, it scans a predefined set of directories for cattackle configurations. Upon discovery, it loads and validates each configuration, registering the cattackle for use by other parts of the system.

## Evolution
### Planned
- Refactor to use FastAPI's `Depends` system for dependency injection, removing the global singleton instance in favor of a managed instance on the application state.
- Caching of registry data to a persistent store like Redis could be a future optimization.
