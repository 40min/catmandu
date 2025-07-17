---
id: TASK-2025-007
title: 'Phase 2: Implement /cattackles API Endpoint'
status: done
priority: high
type: feature
estimate: 'S'
assignee: '@catmandu-devs'
created: 2025-07-16
updated: 2025-07-16
parents: [TASK-2025-001]
arch_refs: [ARCH-core-main-process, ARCH-core-cattackle-registry]
audit_log:
  - {date: 2025-07-16, user: '@AI-DocArchitect', action: 'created with status backlog'}
  - {date: 2025-07-16, user: '@AI-DocArchitect', action: 'status: backlog → done'}
---
## Description
Implement an API endpoint to expose the current state of the Cattackle Registry. This is important for monitoring, debugging, and administration of the bot.

## Acceptance Criteria
- A new GET endpoint `/cattackles` is added to the FastAPI application.
- This endpoint returns a JSON list of all discovered and loaded cattackles.
- Each cattackle in the response includes its ID, name, version, and description.
- The endpoint correctly interacts with the `CattackleRegistry` to fetch the list of cattackles.

## Definition of Done
- The `/cattackles` API endpoint is implemented and functional.
- The endpoint returns the expected data structure.
- Basic tests verify the endpoint's behavior.
