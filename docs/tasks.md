# Phase 1: Foundation (Week 1) - Detailed Tasks

This document breaks down the development tasks for Phase 1 of the RhinoMCP Remote Server MVP using Python and FastMCP SDK.

## 1. Project Initialization (Python/FastMCP)

- [ ] **Task 1.1: Initialize Python project.**
    - **Requirements:** 
        - Create a `pyproject.toml` file (already exists, may need updates).
        - Ensure Python 3.9+ is being used.
        - Set up virtual environment.
- [ ] **Task 1.2: Install FastMCP SDK.**
    - **Requirements:**
        - Add FastMCP as a dependency in `pyproject.toml` or `requirements.txt`.
        - Research FastMCP documentation for WebSocket server setup.
- [ ] **Task 1.3: Define project structure.**
    - **Requirements:**
        - Organize the existing `local_rhino_mcp/` code as reference.
        - Create new `remote_server/` directory for the cloud server implementation.
        - Structure: `remote_server/server.py`, `remote_server/config.py`, etc.
- [ ] **Task 1.4: Set up development tools.**
    - **Requirements:**
        - Configure black (code formatting) and flake8/ruff (linting).
        - Add pre-commit hooks if desired.
        - Update `pyproject.toml` with development dependencies.

## 2. FastMCP HTTP Server (Streamable HTTP Transport)

- [x] **Task 2.1: Research FastMCP server capabilities.**
    - **Requirements:** ✅ **COMPLETED**
        - FastMCP uses HTTP streaming and SSE, not traditional WebSockets
        - `transport="http"` runs on Uvicorn server (ASGI-compatible)
        - Built-in session management and multi-client support
- [ ] **Task 2.2: Create a basic FastMCP HTTP server.**
    - **Requirements:**
        - Implement a server in `remote_server/server.py` using `mcp.run(transport="http")`
        - Configure for Cloud Run deployment (`host="0.0.0.0"`, configurable port)
        - Add health check endpoint using `@mcp.custom_route`
- [ ] **Task 2.3: Implement basic CAD tool definitions.**
    - **Requirements:**
        - Use `@mcp.tool` decorator to define MCP tools for CAD operations
        - Reference existing tools from `local_rhino_mcp/rhino_tools.py`
        - Implement message routing for multiple Rhino instances per user session

## 3. Google Cloud Integration (Redis & PostgreSQL)

- [ ] **Task 3.1: Set up Google Memorystore (Redis).**
    - **Requirements:**
        - Provision a single-node Redis instance on GCP Memorystore within the `reer-remote-rhinomcp` project.
        - Document connection details securely (use Google Secret Manager).
- [ ] **Task 3.2: Integrate Redis client.**
    - **Requirements:**
        - Add `redis-py` or `aioredis` to dependencies.
        - Create a Redis connection module in `remote_server/redis_client.py`.
        - Implement basic session storage functionality.
- [ ] **Task 3.3: Set up Google Cloud SQL (PostgreSQL).**
    - **Requirements:**
        - Provision a PostgreSQL instance on GCP Cloud SQL within the `reer-remote-rhinomcp` project.
        - Create a database and application user.
        - Configure SSL connection and document connection details.
- [ ] **Task 3.4: Integrate database ORM.**
    - **Requirements:**
        - Choose between SQLAlchemy or async alternatives (e.g., `databases` + `asyncpg`).
        - Create database models for users, sessions, and projects.
        - Implement database connection management.

## 4. Docker Development Environment

- [ ] **Task 4.1: Create a `Dockerfile`.**
    - **Requirements:**
        - Create a multi-stage `Dockerfile` for the Python application.
        - Handle dependency installation from `pyproject.toml` or `requirements.txt`.
        - Set up proper Python environment and entry point.
- [ ] **Task 4.2: Create a `docker-compose.yml` file.**
    - **Requirements:**
        - Define services: `server` (Python app), `redis` (local Redis for testing), `postgres` (local Postgres for testing).
        - Configure networking and environment variables.
        - Mount volumes for development with live reloading.
- [ ] **Task 4.3: Add development scripts.**
    - **Requirements:** 
        - Create shell scripts or Makefile for common tasks (`make dev`, `make test`, etc.).
        - Add scripts to `pyproject.toml` if using modern Python tooling.

## 5. Google Cloud Deployment Preparation

- [ ] **Task 5.1: Research Cloud Run deployment for Python.**
    - **Requirements:**
        - Understand Cloud Run requirements for Python WebSocket applications.
        - Research any limitations or special configurations needed.
- [ ] **Task 5.2: Create Cloud Run configuration.**
    - **Requirements:**
        - Create `cloudbuild.yaml` for Google Cloud Build.
        - Configure environment variables and secrets management.
        - Set up basic health checks and logging. 