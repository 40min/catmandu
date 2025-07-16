---
id: TASK-2025-010
title: 'Phase 3: Implement Telegram Polling Loop'
status: backlog
priority: high
type: feature
estimate: 'M'
assignee: '@catmandu-devs'
created: 2025-07-16
updated: 2025-07-16
parents: [TASK-2025-001]
arch_refs: [ARCH-core-telegram-poller, ARCH-core-main-process]
audit_log:
  - {date: 2025-07-16, user: '@AI-DocArchitect', action: 'created with status backlog'}
---
## Description
Implement the primary mechanism for receiving updates from Telegram. This involves creating a background `asyncio` task that continuously polls the Telegram API.

## Acceptance Criteria
- An `asyncio` task is created and started via the FastAPI `lifespan` event.
- The task periodically calls Telegram's `getUpdates` method, managing the `update_id` offset to avoid duplicate processing.
- Upon receiving new updates, it passes them to the `MessageRouter` service for processing.