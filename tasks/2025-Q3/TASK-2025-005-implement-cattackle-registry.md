---
id: TASK-2025-005
title: 'Phase 2: Implement CattackleRegistry Service'
status: backlog
priority: high
type: feature
estimate: 'M'
assignee: '@catmandu-devs'
created: 2025-07-16
updated: 2025-07-16
parents: [TASK-2025-001]
arch_refs: [ARCH-core-cattackle-registry]
audit_log:
  - {date: 2025-07-16, user: '@AI-DocArchitect', action: 'created with status backlog'}
---
## Description
Implement the service to dynamically discover and load cattackle configurations. This service is key to the system's modularity, as it removes the need for manual registration of new cattackles.

## Acceptance Criteria
- A service is created that can scan a specified directory for `cattackle.toml` files.
- The service successfully parses the TOML files into `CattackleConfig` models.
- The parsed configurations are stored in an in-memory collection accessible to other services.