---
layer: application
owner: '@catmandu-devs'
version: v1
status: current
created: 2025-07-16
updated: 2025-07-16
tags: [core, fastapi, poller]
depends_on:
  - ARCH-core-telegram-poller
referenced_by: []
---
# ARCH-core-main-process-v1

## Overview
The Main Process module is the central orchestrator of the Catmandu application. It initializes and manages the core components, including the API server, background task runners, and event handling mechanisms.

## Responsibilities
- Initialize the FastAPI application.
- Load and configure core services (e.g., registry, message router).
- Start background tasks and pollers.
- Handle application lifecycle events.

## Architecture
The main process is built around FastAPI, leveraging its asynchronous capabilities and robust ecosystem. It sets up the application structure, registers necessary components, and ensures smooth operation of all modules.

## Evolution
### Planned
- Integrate with the Cattackle Registry to dynamically load and manage cattackles.
- Implement robust error handling and logging across the application.
