---
id: ARCH-core-main-process
title: "Core: Main Process"
type: component
layer: application
owner: '@catmandu-devs'
version: v1
status: planned
created: 2025-07-16
updated: 2025-07-16
tags: [core, fastapi, poller]
depends_on:
  - ARCH-core-telegram-poller
  - ARCH-core-message-router
referenced_by: []
---
## Context
The Catmandu Core Main Process is the central nervous system of the bot. It serves as the primary entry point and orchestrates all core functionalities. It is designed as a single process that handles both incoming web requests for administration and the primary task of fetching and processing Telegram updates.

## Structure
The process is built around a FastAPI application. It leverages FastAPI's `lifespan` events to manage background tasks.

1.  **FastAPI Web Server:** Runs in the main `asyncio` event loop. It exposes administrative and monitoring endpoints such as `/health`, `/cattackles`, and `/admin/reload`.
2.  **Background Tasks:** A set of `asyncio` tasks that run concurrently with the web server. The most critical background task is the `Telegram Poller`. These tasks are started and stopped gracefully using the `lifespan` manager.

Key file: `main.py`

## Behavior
On startup, the `lifespan` event handler initializes all necessary services (e.g., Cattackle Registry, MCP Client Manager) and starts the Telegram Polling background task. The FastAPI server then begins listening for HTTP requests on its configured port.

The poller continuously fetches updates from the Telegram API and passes them to the Message Router for processing. The web server handles administrative requests in parallel. On shutdown, the `lifespan` event handler gracefully stops the background tasks.

## Evolution
### Planned
- **v1:** Initial implementation using FastAPI with a background polling task.
- Future versions might explore a multi-process architecture if performance requirements demand it, separating the web server from the poller.