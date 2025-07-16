---
id: ARCH-core-telegram-poller
title: "Core: Telegram Poller"
type: component
layer: infrastructure
owner: '@catmandu-devs'
version: v1
status: planned
created: 2025-07-16
updated: 2025-07-16
tags: [core, telegram, poller, asyncio]
depends_on: []
referenced_by: []
---
## Context
The Telegram Poller is a background process responsible for fetching updates from the Telegram Bot API. It uses a long-polling mechanism, which is more resilient to server-side network issues than a webhook, as it initiates the connection from the application side.

## Structure
This component is implemented as an `asyncio` task that runs in an infinite loop. The task is started when the main application starts (via FastAPI's `lifespan` event).

Key file: `catmandu.poller`

## Behavior
Inside its loop, the poller calls the `getUpdates` method of the Telegram API. It uses an `offset` parameter (`update_id`) to ensure it only receives new messages and doesn't process the same update twice. To prevent losing updates on restart, this `offset` will be persisted to a simple file or a Redis key. After fetching a batch of updates, it iterates through them and passes each one to the `MessageRouter` service for processing.

## Evolution
### Planned
- **v1:** Initial implementation with `update_id` offset persisted to a local file.
- A more robust solution using Redis for state management could be implemented later for better scalability and reliability in a distributed environment.