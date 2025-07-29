---
id: TASK-2025-004
title: 'Phase 1: Implement Basic FastAPI App with Lifespan Events'
status: done
priority: high
type: feature
estimate: 'S'
assignee: '@catmandu-devs'
created: 2025-07-16
updated: 2025-07-17
parents: [TASK-2025-001]
arch_refs: [ARCH-core-main-process]
audit_log:
  - {date: 2025-07-16, user: '@AI-DocArchitect', action: 'created with status backlog'}
---
## Description
Create the entry point for the core service. This involves setting up a basic FastAPI application with startup and shutdown events managed by a `lifespan` manager. This is foundational for managing background tasks like the Telegram poller.

## Acceptance Criteria
- A `main.py` file initializes a FastAPI application.
- The application uses a `lifespan` context manager.
- A `/health` endpoint is implemented and returns `{"status": "ok"}`.
- Standard logging is configured for the application.
