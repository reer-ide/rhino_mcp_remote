# Router Modules

This directory contains the modularized API route handlers for the Remote Rhino MCP Server.

## Structure

```
routers/
├── __init__.py          # Package initialization
├── health.py           # Health check and debug endpoints
├── license.py          # License management endpoints  
├── sessions.py         # Session management endpoints
└── README.md           # This file
```

## Modules

### health.py
Contains health check and debugging endpoints:
- `GET /health` - Health check for load balancers
- `POST /cleanup` - Manual cleanup of expired sessions
- `GET /debug/mock-redis` - Mock Redis status (development)
- `POST /debug/mock-redis/clear` - Clear mock Redis data (development)

### license.py
Contains license management endpoints:
- `POST /license/generate` - Generate new license keys (admin)
- `POST /license/register` - Register a license key
- `POST /license/validate` - Validate license key and machine fingerprint
- `GET /license/{license_id}/info` - Get license information

### sessions.py
Contains session management endpoints:
- `POST /sessions/create` - Create new persistent session
- `GET /sessions/active` - Get active sessions for user
- `GET /sessions/pending` - Get pending sessions for auto-reconnection
- `POST /sessions/reconnect` - Reconnect to existing session
- `POST /sessions/{session_id}/reactivate` - Reactivate dormant session
- `GET /sessions/{session_id}/notifications` - SSE endpoint for notifications
- `GET /sessions/{session_id}/status` - Get detailed session status
- `POST /sessions/create_legacy` - Legacy session creation (backward compatibility)

## Design Principles

1. **Separation of Concerns**: Each router handles a specific domain (health, licenses, sessions)
2. **Dependency Injection**: Uses the centralized `dependencies.py` module for manager access
3. **Error Handling**: Consistent error response patterns across all endpoints
4. **Logging**: Comprehensive logging for debugging and monitoring
5. **Type Safety**: Proper type hints and validation
6. **Documentation**: Clear docstrings for all functions

## Usage

Routers are registered with the FastMCP server during initialization:

```python
from remote_server.routers.health import register_health_routes
from remote_server.routers.license import register_license_routes
from remote_server.routers.sessions import register_session_routes

# Register all routes
register_health_routes(mcp)
register_license_routes(mcp)
register_session_routes(mcp)
```

This modular approach makes the codebase more maintainable, testable, and follows modern API development best practices.