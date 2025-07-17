---
id: TASK-2025-006
title: 'Phase 2: Create Reference "Echo" Cattackle'
status: done
priority: high
type: feature
estimate: 'M'
assignee: '@catmandu-devs'
created: 2025-07-16
updated: 2025-07-16
parents: [TASK-2025-001]
arch_refs: [ARCH-cattackle-spec]
audit_log:
  - {date: 2025-07-16, user: '@AI-DocArchitect', action: 'created with status backlog'}
  - {date: 2025-07-16, user: '@AI-DocArchitect', action: 'status: backlog → done'}
---
## Description
Create a simple "echo" cattackle to serve as a reference implementation for future cattackle development. This will also be crucial for end-to-end testing of the core system.

## Acceptance Criteria
- A new directory `cattackles/echo` is created.
- Inside `cattackles/echo`, a `cattackle.toml` file exists with the basic structure.
- A Python module (`src/server.py`) implements the cattackle logic, echoing input messages.
- The echo cattackle can be discovered and loaded by the `CattackleRegistry`.
- The echo cattackle correctly processes and responds to messages.

## Definition of Done
- The "echo" cattackle is fully implemented and integrated.
- Basic tests confirm its functionality.
