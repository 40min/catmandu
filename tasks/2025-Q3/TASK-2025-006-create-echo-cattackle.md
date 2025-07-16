---
id: TASK-2025-006
title: 'Phase 2: Create Reference "Echo" Cattackle'
status: backlog
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
---
## Description
Create a simple "echo" cattackle to serve as a reference implementation for future cattackle development. This will also be crucial for end-to-end testing of the core system.

## Acceptance Criteria
- A new directory `cattackles/echo` is created.
- The directory contains a valid `cattackle.toml`, a `requirements.txt`, and a `src/server.py`.
- The `server.py` implements a `FastMCP` server with an "echo" function that returns its input arguments.