# Layered Architecture for Catmandu Core

## Overview

Catmandu follows a clean, layered architecture pattern that separates concerns between external interfaces (clients), business logic (services), and data access (repositories). This document outlines the architectural approach and provides guidelines for maintaining this separation.

## Architecture Layers

### 1. Client Layer (`core/clients/`)

The client layer provides thin wrappers around external APIs and protocols, focusing on transport concerns only.

**Responsibilities:**
- HTTP/WebSocket/STDIO communication
- Protocol handling
- Connection management
- Error handling related to transport

**Key Characteristics:**
- Stateless or minimal state
- No business logic
- Focus on transport concerns
- Easy to mock in tests

**Examples:**
- `TelegramClient`: Wraps Telegram Bot API
- `McpClient`: Wraps Model Context Protocol

### 2. Service Layer (`core/services/`)

The service layer contains the core business logic and orchestrates operations using clients.

**Responsibilities:**
- Business workflows
- State management
- Coordination between multiple clients
- Domain-specific error handling
- Retry logic and resilience patterns

**Key Characteristics:**
- Stateful
- Contains business rules
- Uses clients for external communication
- Implements domain logic

**Examples:**
- `McpService`: Manages cattackle execution with retry logic
- `MessageRouter`: Routes messages to appropriate cattackles
- `TelegramPoller`: Orchestrates polling and message processing

### 3. Repository Layer (`core/repositories/`) - Future

The repository layer will abstract data storage and retrieval operations.

**Responsibilities:**
- Data access abstraction
- Storage operations
- Query operations
- Data transformation

**Key Characteristics:**
- Domain-focused interface
- Storage technology agnostic
- Handles persistence concerns

**Examples:**
- `CattackleRepository`: Stores and retrieves cattackle data
- `MessageRepository`: Manages message history

## Dependency Direction

Dependencies flow inward:
- Services depend on Clients
- API endpoints depend on Services
- Clients don't depend on Services

```
API Endpoints → Services → Clients → External Systems
```

## Benefits of This Architecture

1. **Testability**: Each layer can be tested in isolation with appropriate mocks
2. **Maintainability**: Changes to external APIs only affect the client layer
3. **Flexibility**: Easy to swap implementations (e.g., different transport protocols)
4. **Separation of Concerns**: Clear responsibilities for each component
5. **Reusability**: Clients can be reused across different services

## Guidelines for Development

1. **Keep Clients Thin**: Clients should only handle transport concerns, not business logic
2. **Services Own Business Logic**: All business rules and workflows belong in services
3. **Dependency Injection**: Use DI to provide clients to services
4. **Clear Interfaces**: Define clear interfaces between layers
5. **Error Handling**: Transport errors in clients, business errors in services

## Example: Message Processing Flow

1. `TelegramPoller` (Service) uses `TelegramClient` (Client) to get updates
2. `TelegramPoller` passes updates to `MessageRouter` (Service)
3. `MessageRouter` identifies the target cattackle and uses `McpService` (Service)
4. `McpService` uses `McpClient` (Client) to communicate with the cattackle
5. Response flows back through the same layers
