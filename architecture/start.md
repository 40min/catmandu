# Implementation Plan: Catmandu Core System

## 1. Executive Summary & Goals
This document outlines the engineering plan to implement the foundational infrastructure for the "Catmandu" modular Telegram bot, based on the provided Product Requirements Document (PRD) and subsequent updates.

The primary goals are:
-   **Establish Core Service:** Build a robust core service that polls the Telegram API for updates and runs a FastAPI server for operational endpoints.
-   **Enable Modularity:** Implement a dynamic cattackle discovery and registration system that allows new features to be added without changing the core codebase.
-   **Implement Communication Protocol:** Integrate the MCP (Model Context Protocol) to facilitate standardized, language-agnostic communication between the Catmandu Core and individual cattackle modules.

## 2. Current Situation Analysis
The project, now named `catmandu`, consists of an empty `cattackles` directory and a detailed PRD. There is no existing application code. The PRD provides a clear architectural vision, which this plan adapts to incorporate a polling-based approach for Telegram updates, as requested. The immediate task is to translate this updated architectural design into a structured, buildable project using `uv` for package management.

## 3. Proposed Solution / Refactoring Strategy
### 3.1. High-Level Design / Architectural Overview
The proposed system's Catmandu Core acts as a central nervous system. A dedicated background process will continuously poll the Telegram API for new updates. Upon receiving an update, it will pass it to a Message Router which identifies the target command, routes the request to the appropriate Cattackle micro-service via the MCP protocol, and relays the response back to the user. The FastAPI server will run in parallel to handle administrative and monitoring endpoints.

```mermaid
graph TD
    subgraph User
        Telegram_User
    end

    subgraph External
        Telegram_API[Telegram Bot API]
    end

    subgraph Catmandu Core Process
        direction LR
        subgraph "Background Tasks"
            Telegram_Poller[Telegram Poller]
        end
        subgraph "Web Server"
            FastAPI_Server[FastAPI Server<br>/health, /cattackles]
        end

        Telegram_Poller --> MessageRouter{Message Router}
        MessageRouter --> CattackleRegistry[Cattackle Registry<br>(In-Memory Cache)]
        MessageRouter --> MCP_Client_Manager[MCP Client Manager]
    end

    subgraph Cattackle Processes
        direction TB
        Cattackle_Echo[Echo Cattackle (Python)<br>FastMCP Server]
        Cattackle_Weather[Weather Cattackle (JS)<br>FastMCP Server]
        Cattackle_Other[...]
    end

    Telegram_User --sends /command--> Telegram_API
    Telegram_Poller --polls for updates--> Telegram_API
    MCP_Client_Manager --MCP Call--> Cattackle_Echo
    MCP_Client_Manager --MCP Call--> Cattackle_Weather
    MCP_Client_Manager --MCP Call--> Cattackle_Other
```
*Diagram: Flow of a user command through the Catmandu polling system.*

### 3.2. Key Components / Modules
1.  **Project Structure (`catmandu/src`):** A new Python project will be created to house the core logic.
2.  **Core Models (`catmandu.core.models`):** Pydantic models will define the data contracts, including `CattackleRequest`, `CattackleResponse`, and a model for parsing `cattackle.toml` files.
3.  **Telegram Poller (`catmandu.poller`):** A background `asyncio` task responsible for fetching updates from the Telegram API at regular intervals and dispatching them to the Message Router.
4.  **Cattackle Registry (`catmandu.services.registry`):** A singleton service for discovering cattackles by scanning the `cattackles` directory at startup and parsing `cattackle.toml` files.
5.  **MCP Client Manager (`catmandu.services.mcp_client`):** A service that abstracts communication with cattackle processes via the `mcp-client` library.
6.  **Message Router (`catmandu.services.router`):** A service containing the primary business logic for parsing messages, identifying the target cattackle, and orchestrating the request/response flow.
7.  **API Endpoints (`catmandu.api`):** A set of FastAPI routers for handling `/health`, `/cattackles`, and other administrative endpoints. The Telegram webhook endpoint is no longer required.
8.  **Reference Cattackle (`cattackles/echo`):** A simple "echo" cattackle to serve as a reference implementation.

### 3.3. Detailed Action Plan / Phases
#### Phase 1: Foundation and Scaffolding
-   **Objective(s):** Establish the project structure, dependencies using `uv`, core data models, and basic application setup.
-   **Priority:** High
-   **Task 1.1:** Initialize Python Project Structure with `uv`
    -   **Rationale/Goal:** Create a standard, scalable project layout using the modern `uv` package manager.
    -   **Estimated Effort:** S
    -   **Deliverable/Criteria for Completion:** A `catmandu` directory with a `pyproject.toml` configured for use with `uv`, a `src/catmandu` subdirectory, and a `tests` directory.
-   **Task 1.2:** Define Core Pydantic Models
    -   **Rationale/Goal:** Create the strict data contracts for all system communication.
    -   **Estimated Effort:** S
    -   **Deliverable/Criteria for Completion:** A `models.py` file containing `CattackleRequest`, `CattackleResponse`, and `CattackleConfig` Pydantic models.
-   **Task 1.3:** Implement Basic FastAPI Application with Lifespan Events
    -   **Rationale/Goal:** Create the entry point for the core service and set up startup/shutdown events to manage background tasks.
    -   **Estimated Effort:** S
    -   **Deliverable/Criteria for Completion:** A `main.py` that initializes a FastAPI app with a `lifespan` manager. A working `/health` endpoint is available. Standard logging is configured.

#### Phase 2: Cattackle Discovery and Reference Implementation
-   **Objective(s):** Implement the mechanism for finding and registering cattackles. Create the first working cattackle.
-   **Priority:** High
-   **Task 2.1:** Implement `CattackleRegistry` Service
    -   **Rationale/Goal:** To dynamically discover and load cattackle configurations without manual registration.
    -   **Estimated Effort:** M
    -   **Deliverable/Criteria for Completion:** A service that scans a directory for `cattackle.toml` files, parses them, and stores the configuration in memory.
-   **Task 2.2:** Create Reference "Echo" Cattackle
    -   **Rationale/Goal:** Provide a working example for future cattackle developers and for end-to-end testing.
    -   **Estimated Effort:** M
    -   **Deliverable/Criteria for Completion:** A new directory `cattackles/echo` with a `cattackle.toml`, `requirements.txt`, and a `src/server.py` that implements a `FastMCP` server with an "echo" function.
-   **Task 2.3:** Implement `/cattackles` API Endpoint
    -   **Rationale/Goal:** To expose the state of the Cattackle Registry for monitoring and debugging.
    -   **Estimated Effort:** S
    -   **Deliverable/Criteria for Completion:** A GET `/cattackles` endpoint that returns a JSON list of all discovered cattackle configurations.

#### Phase 3: Core Logic and End-to-End Communication
-   **Objective(s):** Wire all components together to process a Telegram message from polling to response.
-   **Priority:** High
-   **Task 3.1:** Implement `MCPClientManager` Service
    -   **Rationale/Goal:** To create a dedicated, testable layer for handling all MCP communication.
    -   **Estimated Effort:** M
    -   **Deliverable/Criteria for Completion:** A service with a `call_cattackle` method that executes a remote call using `mcp-client`.
-   **Task 3.2:** Implement `MessageRouter` Service
    -   **Rationale/Goal:** To encapsulate the main business logic of routing a message.
    -   **Estimated Effort:** M
    -   **Deliverable/Criteria for Completion:** A service that takes a Telegram message object, parses it, finds the target cattackle, and orchestrates the MCP call.
-   **Task 3.3:** Implement Telegram Polling Loop
    -   **Rationale/Goal:** To establish the primary mechanism for receiving updates from Telegram.
    -   **Estimated Effort:** M
    -   **Deliverable/Criteria for Completion:** An `asyncio` task, started via the FastAPI `lifespan` event, that periodically calls Telegram's `getUpdates` method, and upon receiving updates, passes them to the `MessageRouter` for processing.
-   **Task 3.4:** Create Integration Test for Message Flow
    -   **Rationale/Goal:** To validate that all components work together correctly.
    -   **Estimated Effort:** M
    -   **Deliverable/Criteria for Completion:** A pytest integration test that mocks the Telegram API client's `getUpdates` method to return a sample message, then asserts that the `MessageRouter` and `MCPClientManager` are called correctly.

#### Phase 4: Operability and Deployment
-   **Objective(s):** Prepare the application for deployment and improve operational management.
-   **Priority:** Medium
-   **Task 4.1:** Implement `/admin/reload` Endpoint
    -   **Rationale/Goal:** To allow hot-reloading of cattackle configurations.
    -   **Estimated Effort:** S
    -   **Deliverable/Criteria for Completion:** A POST `/admin/reload` endpoint that triggers the `CattackleRegistry` to re-scan its directory.
-   **Task 4.2:** Containerize Applications
    -   **Rationale/Goal:** To ensure a consistent and reproducible deployment environment.
    -   **Estimated Effort:** M
    -   **Deliverable/Criteria for Completion:** A `Dockerfile` for Catmandu Core and one for the reference Echo Cattackle.
-   **Task 4.3:** Create Docker Compose Setup
    -   **Rationale/Goal:** To simplify local development and testing.
    -   **Estimated Effort:** M
    -   **Deliverable/Criteria for Completion:** A `docker-compose.yml` file that defines services for the Catmandu Core, the Echo Cattackle, and a Redis instance.

### 3.4. Data Model Changes
No database schema changes are required. The primary data models are in-memory application models defined using Pydantic, based on the PRD.

### 3.5. API Design / Interface Changes
The plan will implement the API endpoints as specified in the PRD, with the removal of the Telegram webhook.
-   `GET /health`: Returns `{"status": "ok"}`.
-   `GET /cattackles`: Returns a `List[CattackleConfig]`.
-   `POST /admin/reload`: Accepts no body. Returns `{"status": "reloaded", "found": <count>}`.

## 4. Key Considerations & Risk Mitigation
### 4.1. Technical Risks & Challenges
-   **Risk:** Managing the state of the Telegram poller, specifically the `update_id` offset, to avoid missing or reprocessing updates on restart.
    -   **Mitigation:** The `update_id` offset can be persisted to a simple file or a Redis key. The poller will read this value on startup and save the latest `update_id` after each successful batch of processing.
-   **Risk:** The `mcp-client` library may have a steep learning curve or bugs.
    -   **Mitigation:** Encapsulate all direct interaction with the library inside the `MCPClientManager` to isolate the dependency.
-   **Risk:** Managing lifecycles of Cattackle sub-processes.
    -   **Mitigation:** The initial implementation will not manage cattackle processes. `docker-compose` will handle this for local development, and a production orchestrator (like Kubernetes) is expected for production.

### 4.2. Dependencies
-   **Internal:** The phases are designed to be sequential.
-   **External Libraries:** `fastapi`, `uvicorn`, `pydantic`, `python-telegram-bot`, `toml`, and `mcp-client`. The plan assumes these are available, stable, and installable via `uv`.

### 4.3. Non-Functional Requirements (NFRs) Addressed
-   **Modularity:** The core design ensures a strict separation between the core and cattackles via the MCP interface.
-   **Maintainability:** Achieved through Separation of Concerns into distinct, testable components (Poller, Router, Registry, MCP Client).
-   **Reliability:** The change to polling makes the system resilient to temporary network issues on the server side, as it controls the communication initiation. State management for the `update_id` is crucial for message delivery guarantees.

## 5. Success Metrics / Validation Criteria
-   The full test suite, including unit and integration tests, passes.
-   When the system is running via `docker-compose`, the poller correctly fetches updates. Sending a `/echo <text>` command to the bot in Telegram results in the bot replying with `<text>`.
-   A GET request to the `/cattackles` endpoint returns a JSON object correctly describing the "echo" cattackle.

## 6. Assumptions Made
-   `uv` is the chosen package manager and is installed in the development environment.
-   The `python-telegram-bot` library provides a robust and straightforward `asyncio`-compatible interface for long polling.
-   The `mcp-client` and `FastMCP` libraries are available and stable.
-   Secrets like the `TELEGRAM_BOT_TOKEN` will be managed via environment variables.
-   User-level permission checks (`PermissionManager`) are out of scope for this initial implementation.

## 7. Open Questions / Areas for Further Investigation
-   What is the specific connection management strategy for the `MCPClientManager`? (e.g., persistent connections, connection pooling). The initial plan will assume simple, on-demand connections, with pooling as a future optimization.
