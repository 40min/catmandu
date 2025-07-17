---
id: TASK-2025-015
title: "Refactor Core Services to use FastAPI Dependency Injection"
status: backlog
priority: high
type: tech_debt
estimate: 'M'
assignee: '@catmandu-devs'
created: 2025-07-16
updated: 2025-07-16
children: [TASK-2025-016]
arch_refs: [ARCH-core-cattackle-registry, ARCH-core-main-process]
audit_log:
  - {date: 2025-07-16, user: '@AI-DocArchitect', action: 'created with status backlog'}
---
## Description
This task is to refactor the Catmandu Core application to replace the current global singleton pattern for services with FastAPI's built-in Dependency Injection (`Depends`) system. This change will make dependencies explicit, improve the testability of API endpoints, and align the codebase with modern FastAPI best practices. This is a parent task for the overall refactoring effort.

## Acceptance Criteria
- Global service instances (like `cattackle_registry`) are eliminated.
- Services are instantiated once on application startup within the `lifespan` context manager and stored in `app.state`.
- API endpoints receive service instances via `Depends`.
- The application is fully testable with `dependency_overrides`.

## Definition of Done
- All child tasks are completed.
- The application functions as before the refactoring.
