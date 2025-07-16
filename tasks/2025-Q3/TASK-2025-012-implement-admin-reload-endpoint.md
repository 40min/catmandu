---
id: TASK-2025-012
title: 'Phase 4: Implement /admin/reload Endpoint'
status: backlog
priority: medium
type: feature
estimate: 'S'
assignee: '@catmandu-devs'
created: 2025-07-16
updated: 2025-07-16
parents: [TASK-2025-001]
arch_refs: [ARCH-core-cattackle-registry]
audit_log:
  - {date: 2025-07-16, user: '@AI-DocArchitect', action: 'created with status backlog'}
---
## Description
Implement an administrative endpoint to allow hot-reloading of cattackle configurations without restarting the core service.

## Acceptance Criteria
- A `POST /admin/reload` endpoint is created.
- When called, this endpoint triggers the `CattackleRegistry` to re-scan its directory for `cattackle.toml` files.
- The endpoint returns a success status with a count of found cattackles, e.g., `{"status": "reloaded", "found": 1}`.