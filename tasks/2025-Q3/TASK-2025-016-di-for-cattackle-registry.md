---
id: TASK-2025-016
title: "DI Refactor: Convert CattackleRegistry to an Injected Dependency"
status: done
priority: high
type: tech_debt
estimate: 'S'
assignee: '@catmandu-devs'
created: 2025-07-16
updated: 2025-07-18
parents: [TASK-2025-015]
arch_refs: [ARCH-core-cattackle-registry, ARCH-core-main-process]
audit_log:
  - {date: 2025-07-16, user: '@AI-DocArchitect', action: 'created with status backlog'}
  - {date: 2025-07-18, user: '@Robotic-SSE', action: 'status: backlog → done. The initial implementation already follows DI principles.'}
---
## Description
This task covers the conversion of the `CattackleRegistry` from a global singleton to a dependency managed and injected by FastAPI. This involves removing the global instance, managing its lifecycle via `app.state` and the `lifespan` manager, creating a dependency provider function, and updating the API endpoint to use `Depends`.

## Acceptance Criteria
- The global `cattackle_registry` instance is removed from `src/catmandu/core/services/registry.py`.
- The `CattackleRegistry` instance is created on application startup in `main.py` and stored in `app.state`.
- A `get_cattackle_registry` dependency provider function is created in `src/catmandu/api/dependencies.py`.
- The `/cattackles` endpoint in `src/catmandu/api/cattackles.py` receives its `CattackleRegistry` instance via `Depends`.

## Definition of Done
- Code is refactored as per the acceptance criteria.
- The application starts and the `/cattackles` endpoint functions correctly.
- A new unit test is created that uses `app.dependency_overrides` to inject a mock `CattackleRegistry`.
