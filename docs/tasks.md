# Phase 1: Foundation (Week 1) - Detailed Tasks

This document breaks down the development tasks for Phase 1 of the RhinoMCP Remote Server MVP using Python and FastMCP SDK.

## 1. Project Initialization (Python/FastMCP)

- [x] **Task 1.1: Initialize Python project.** ✅ **COMPLETED**
    - **Requirements:** 
        - Create a `pyproject.toml` file (already exists, may need updates).
        - Ensure Python 3.9+ is being used.
        - Set up virtual environment.
- [x] **Task 1.2: Install FastMCP SDK.** ✅ **COMPLETED**
    - **Requirements:**
        - Add FastMCP as a dependency in `pyproject.toml` or `requirements.txt`.
        - Research FastMCP documentation for WebSocket server setup.
- [x] **Task 1.3: Define project structure.** ✅ **COMPLETED**
    - **Requirements:**
        - Organize the existing `local_rhino_mcp/` code as reference.
        - Create new `remote_server/` directory for the cloud server implementation.
        - Structure: `remote_server/server.py`, `remote_server/config.py`, etc.
- [x] **Task 1.4: Set up development tools.** ✅ **COMPLETED**
    - **Requirements:**
        - Configure black (code formatting) and flake8/ruff (linting).
        - Add pre-commit hooks if desired.
        - Update `pyproject.toml` with development dependencies.

## 2. FastMCP HTTP Server (Streamable HTTP Transport)

- [x] **Task 2.1: Research FastMCP server capabilities.** ✅ **COMPLETED**
    - **Requirements:** 
        - FastMCP uses HTTP streaming and SSE, not traditional WebSockets
        - `transport="http"` runs on Uvicorn server (ASGI-compatible)
        - Built-in session management and multi-client support
- [x] **Task 2.2: Create a basic FastMCP HTTP server.** ✅ **COMPLETED**
    - **Requirements:**
        - Implement a server in `remote_server/server.py` using `mcp.run(transport="http")`
        - Configure for Cloud Run deployment (`host="0.0.0.0"`, configurable port)
        - Add health check endpoint using `@mcp.custom_route`
- [x] **Task 2.3: Implement basic CAD tool definitions.** ✅ **COMPLETED**
    - **Requirements:**
        - Use `@mcp.tool` decorator to define MCP tools for CAD operations
        - Reference existing tools from `local_rhino_mcp/rhino_tools.py`
        - Implement message routing for multiple Rhino instances per user session

## 3. Bidirectional Connection System

- [x] **Task 3.1: Implement Connection Manager** ✅ **COMPLETED**
    - **Requirements:**
        - Create `remote_server/connection_manager.py` with ConnectionSession dataclass
        - Implement session creation with unique tokens and WebSocket ports
        - Add Redis integration for session persistence
        - Create dynamic WebSocket server allocation per session

- [x] **Task 3.2: Add Session Management Endpoints** ✅ **COMPLETED**
    - **Requirements:**
        - Implement `/sessions/create` endpoint for host app integration
        - Add session status resource endpoint
        - Implement connection token validation
        - Add session cleanup and timeout handling

- [x] **Task 3.3: Implement WebSocket Communication** ✅ **COMPLETED**
    - **Requirements:**
        - Create WebSocket server for Rhino plugin connections
        - Implement message correlation system for request/response matching
        - Add connection authentication using tokens
        - Handle connection lifecycle (connect, disconnect, reconnect)
        
## 4. Google Cloud Integration (Redis & PostgreSQL)

- [ ] **Task 4.1: Set up Google Memorystore (Redis).**
    - **Requirements:**
        - Provision a single-node Redis instance on GCP Memorystore within the `reer-remote-rhinomcp` project.
        - Document connection details securely (use Google Secret Manager).
- [ ] **Task 4.2: Integrate Redis client.**
    - **Requirements:**
        - Add `redis-py` or `aioredis` to dependencies.
        - Create a Redis connection module in `remote_server/redis_client.py`.
        - Implement session storage and retrieval functionality.
- [ ] **Task 4.3: Set up Google Cloud SQL (PostgreSQL).**
    - **Requirements:**
        - Provision a PostgreSQL instance on GCP Cloud SQL within the `reer-remote-rhinomcp` project.
        - Create a database and application user.
        - Configure SSL connection and document connection details.
- [ ] **Task 4.4: Integrate database ORM.**
    - **Requirements:**
        - Choose between SQLAlchemy or async alternatives (e.g., `databases` + `asyncpg`).
        - Create database models for users, sessions, and projects.
        - Implement database connection management.

## 5. Docker Development Environment

- [ ] **Task 5.1: Create a `Dockerfile`.**
    - **Requirements:**
        - Create a multi-stage `Dockerfile` for the Python application.
        - Handle dependency installation from `pyproject.toml` or `requirements.txt`.
        - Set up proper Python environment and entry point.
        - Expose both HTTP (8080) and WebSocket (8100+) ports
- [ ] **Task 5.2: Create a `docker-compose.yml` file.**
    - **Requirements:**
        - Define services: `server` (Python app), `redis` (local Redis for testing), `postgres` (local Postgres for testing).
        - Configure networking and environment variables.
        - Mount volumes for development with live reloading.
        - Add port mappings for WebSocket port range
- [ ] **Task 5.3: Add development scripts.**
    - **Requirements:** 
        - Create shell scripts or Makefile for common tasks (`make dev`, `make test`, etc.).
        - Add scripts to `pyproject.toml` if using modern Python tooling.

## 6. Google Cloud Deployment Preparation

- [ ] **Task 6.1: Research Cloud Run deployment for Python.**
    - **Requirements:**
        - Understand Cloud Run requirements for Python WebSocket applications.
        - Research port allocation and dynamic port binding for WebSocket servers.
        - Investigate Cloud Run's support for multiple ports per service.
- [ ] **Task 6.2: Create Cloud Run configuration.**
    - **Requirements:**
        - Create `cloudbuild.yaml` for Google Cloud Build.
        - Configure environment variables and secrets management.
        - Set up basic health checks and logging.
        - Handle dynamic port allocation for WebSocket connections.

## 7. Testing and Integration

- [x] **Task 7.1: Create integration tests** ✅ **COMPLETED**
    - **Requirements:**
        - Test complete connection flow from host app to Rhino
        - Test session creation and management
        - Test WebSocket communication and message routing
        - Test error handling and reconnection scenarios

- [x] **Task 7.2: Create host app integration example** ✅ **COMPLETED**
    - **Requirements:**
        - Create simple host app example using the RhinoConnector class
        - Test file selection and connection establishment flow
        - Implement basic CAD operation testing
        - Add error handling and user feedback

- [ ] **Task 7.3: Enhanced Rhino plugin testing**
    - **Requirements:**
        - Test plugin HTTP server and WebSocket client
        - Test authorization UI and user interaction
        - Test command execution and response handling
        - Test connection persistence and recovery

## Implementation Priority

### Phase 1A: Core Connection System (Week 1-2)
- Tasks 3.1-3.4 (Bidirectional Connection System)
- Basic testing and validation

### Phase 1B: Cloud Integration (Week 2-3)
- Tasks 4.1-4.4 (Google Cloud Integration)
- Docker environment setup (Tasks 5.1-5.3)

### Phase 1C: Deployment and Testing (Week 3-4)
- Tasks 6.1-6.2 (Cloud Deployment)
- Tasks 7.1-7.3 (Testing and Integration)

This updated task list reflects the bidirectional connection architecture and provides a clear path for implementing the complete system. 