---
id: TASK-2025-011
title: 'Phase 3: Create Integration Test for Message Flow'
status: backlog
priority: high
type: chore
estimate: 'M'
assignee: '@catmandu-devs'
created: 2025-07-16
updated: 2025-07-16
parents: [TASK-2025-001]
arch_refs:
  - ARCH-core-message-router
  - ARCH-core-mcp-client-manager
  - ARCH-core-telegram-poller
audit_log:
  - {date: 2025-07-16, user: '@AI-DocArchitect', action: 'created with status backlog'}
---
## Description
Create an integration test to validate that all core components work together correctly, from receiving a message to dispatching it to a cattackle.

## Acceptance Criteria
- A `pytest` integration test is written.
- The test mocks the Telegram API client's `getUpdates` method to return a sample message.
- It then asserts that the `MessageRouter` and `MCPClientManager` are called with the correct parameters, simulating a full, successful message processing flow.