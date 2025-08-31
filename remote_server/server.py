"""
Main FastMCP server for Remote Rhino CAD integration.
Refactored for modularity and maintainability.
"""

import json
from datetime import datetime
from fastmcp import FastMCP
from fastmcp.utilities.logging import get_logger

from remote_server.config import settings
from remote_server.dependencies import get_app_connection_manager, initialize_managers
from remote_server.api.routes.health import register_health_routes
from remote_server.api.routes.license import register_license_routes
from remote_server.api.routes.sessions import register_session_routes
from remote_server.tools import rhinoscript_tools

# Use FastMCP's logging system
logger = get_logger(__name__)


# Create FastMCP server instance  
mcp = FastMCP(
    name="remote-rhino-mcp-server",
    instructions="""
        This is a remote MCP server for Rhino(by Robert McNeel & Associates).
        It is used to connect to a user's local Rhino CAD instance and perform operations on it.
        
        IMPORTANT: All Rhino tool functions require a session_id parameter to identify which 
        connected Rhino instance to communicate with. Make sure to use the session_id from 
        the session creation response.
        """,
)


def register_all_tools():
    """Register all MCP tools with the server."""
    # Import tool modules
    from remote_server.tools import (
        scene_tools,
        object_tools,
        selection_tools,
        metadata_tools,
        layer_tools,
        viewport_tools,
        utility_tools,
        documentation_tools,
        ai_render_tools,
    )
    
    # Register tools with the mcp instance only
    # Connection manager will be accessed lazily when tools are called
    scene_tools.register_tools(mcp, None)
    object_tools.register_tools(mcp, None)
    selection_tools.register_tools(mcp, None)
    metadata_tools.register_tools(mcp, None)
    layer_tools.register_tools(mcp, None)
    viewport_tools.register_tools(mcp, None)
    utility_tools.register_tools(mcp, None)
    rhinoscript_tools.register_tools(mcp, None)
    documentation_tools.register_tools(mcp, None)
    ai_render_tools.register_tools(mcp, None)
    
    logger.info("All MCP tools registered successfully")


async def initialize_server():
    """Initialize the server with managers and routes."""
    # Initialize managers
    await initialize_managers()
    
    # Register all routes
    register_health_routes(mcp)
    register_license_routes(mcp)
    register_session_routes(mcp)
    
    # Register MCP tools
    register_all_tools()
    
    logger.info("Server initialization complete")


@mcp.resource("sessions/{session_id}/status")
async def get_session_status_resource(session_id: str) -> str:
    """Get connection session status as MCP resource"""
    try:
        from remote_server.dependencies import get_connection_manager
        connection_manager = await get_connection_manager()
        session = await connection_manager.get_session(session_id)
        if not session:
            return json.dumps({"error": "Session not found"})
        
        return json.dumps({
            "session_id": session.session_id,
            "user_id": session.user_id,
            "license_id": session.license_id,
            "status": session.status,
            "instance_id": session.instance_id,
            "file_path": session.file_path,
            "created_at": session.created_at.isoformat(),
            "last_active": session.last_active.isoformat(),
            "expires_at": session.expires_at.isoformat(),
            "websocket_port": session.websocket_port
        })
    except Exception as e:
        logger.error(f"Error getting session status: {e}")
        return json.dumps({"error": str(e)})


@mcp.resource("server://info")
def server_info() -> str:
    """Get server information and status."""
    from remote_server.dependencies import _connection_manager
    
    info = {
        "name": "remote-rhino-mcp-server",
        "version": "0.1.0",
        "description": "Remote MCP server for Rhino CAD integration with persistent sessions",
        "architecture": "license_based_persistent_sessions",
        "timestamp": datetime.now().isoformat(),
        "settings": {
            "host": settings.host,
            "port": settings.port,
            "debug": settings.debug,
        },
        "valid_sessions": len(_connection_manager.sessions) if _connection_manager else 0,
        "active_licenses": 0,  # This would need to be implemented properly
        "features": [
            "license_registration",
            "persistent_sessions", 
            "auto_reconnection",
            "file_integrity_validation",
            "enhanced_session_lifecycle"
        ],
        "available_tools": [
            "get_rhino_scene_info",
            "get_rhino_objects_info",
            "add_rhino_objects_metadata",
            "update_rhino_objects_metadata",
            "create_rhino_basic_objects",
            "create_rhino_layers",
            "delete_rhino_layers",
            "delete_rhino_objects",
            "modify_rhino_objects",
            "capture_rhino_viewport",
            "execute_rhino_code",
            "get_rhino_selected_objects",
            "select_filtered_rhino_objects",
            "look_up_RhinoScriptSyntax",
            "ai_render_rhino_scene",
        ]
    }
    return str(info)


def main():
    """Main entry point for the server."""
    import signal
    import sys
    
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal, stopping server...")
        sys.exit(0)
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info(f"Starting Remote Rhino MCP Server v2.0 on {settings.host}:{settings.port}")
    logger.info("Architecture: License-based persistent sessions with auto-reconnection")
    logger.info("Available Rhino tools: get_rhino_scene_info, get_rhino_objects_info, add_rhino_objects_metadata, update_rhino_objects_metadata, create_rhino_basic_objects, create_rhino_layers, delete_rhino_layers, delete_rhino_objects, modify_rhino_objects, capture_rhino_viewport, execute_rhino_code, get_rhino_selected_objects, select_filtered_rhino_objects, look_up_RhinoScriptSyntax")
    
    # Register routes and tools synchronously (non-async parts)
    register_health_routes(mcp)
    register_license_routes(mcp)
    register_session_routes(mcp)
    register_all_tools()
    
    logger.info("Routes and tools registered")
    
    try:
        # Use FastMCP's built-in run method for proper lifespan management
        # This ensures task groups are properly initialized
        mcp.run(
            transport="http",
            host=settings.host,
            port=settings.port,
            log_level=settings.log_level
        )
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
    except Exception as e:
        logger.error(f"Server error: {e}")
    finally:
        logger.info("Server shutdown complete")


if __name__ == "__main__":
    main()