---
id: TASK-2025-009
title: 'Phase 3: Implement MessageRouter Service'
status: done
priority: high
type: feature
estimate: 'M'
assignee: '@catmandu-devs'
created: 2025-07-16
updated: 2025-07-16
parents: [TASK-2025-001]
arch_refs: [ARCH-core-mcp-client-manager, ARCH-cattackle-spec]
audit_log:
  - {date: 2025-07-16, user: '@AI-DocArchitect', action: 'created with status backlog'}
---
## Description
Implement the service that encapsulates the main business logic of routing a Telegram message. This component is the orchestrator for processing user commands.

## Acceptance Criteria
- A service is created that accepts a Telegram message object.
- The service correctly parses the message to identify the command.
- It queries the `CattackleRegistry` to find the target cattackle.
- It uses the `MCPClientManager` to orchestrate the call to the cattackle and handles the response.
