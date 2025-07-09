"""
Main FastMCP server for Remote Rhino CAD integration.
"""

import logging
from datetime import datetime
from typing import Dict, Any

from fastmcp import FastMCP
from fastmcp.utilities.logging import get_logger
from starlette.requests import Request
from starlette.responses import JSONResponse

from .config import settings
from .connection_manager import ConnectionManager
from .tools import RhinoTools
import asyncio
import json

# Use FastMCP's logging system
logger = get_logger(__name__)

# Create FastMCP server instance
mcp = FastMCP(
    name = "remote-rhino-mcp-server",
    instructions= """
        This is a remote MCP server for Rhino(by Robert McNeel & Associates).
        It is used to connect to a user's local Rhino CAD instance and perform operations on it.
        
        IMPORTANT: All Rhino tool functions require a session_id parameter to identify which 
        connected Rhino instance to communicate with. Make sure to use the session_id from 
        the session creation response.
        """,
    )

# Create connection manager instance
connection_manager = ConnectionManager(redis_url=settings.redis_connection_url)

# Initialize Rhino tools with the connection manager
rhino_tools = RhinoTools(mcp, connection_manager)

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint for load balancers and monitoring."""
    return JSONResponse({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "server": "remote-rhino-mcp-server",
        "version": "0.1.0"
    })

@mcp.custom_route("/cleanup", methods=["POST"])
async def cleanup_expired_sessions(request: Request) -> JSONResponse:
    """Manual cleanup endpoint for expired sessions"""
    try:
        await connection_manager.cleanup_expired_sessions()
        return JSONResponse({
            "status": "success",
            "message": "Expired sessions cleaned up",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        return JSONResponse(
            {"error": "Failed to cleanup sessions"}, 
            status_code=500
        )

@mcp.custom_route("/sessions/create", methods=["POST"])
async def create_session(request: Request) -> JSONResponse:
    """Create a new connection session"""
    try:
        data = await request.json()
        user_id = data.get("user_id")
        file_path = data.get("file_path")
        
        if not user_id or not file_path:
            return JSONResponse(
                {"error": "user_id and file_path are required"}, 
                status_code=400
            )
        
        session = await connection_manager.create_session(user_id, file_path)
        
        # Use 127.0.0.1 for client connections instead of 0.0.0.0 bind address
        client_host = "127.0.0.1" if settings.host == "0.0.0.0" else settings.host
        
        return JSONResponse({
            "session_id": session.session_id,
            "connection_token": session.connection_token,
            "websocket_port": session.websocket_port,
            "websocket_url": f"ws://{client_host}:{session.websocket_port}?token={session.connection_token}",
            "expires_at": session.expires_at.isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        return JSONResponse(
            {"error": "Failed to create session"}, 
            status_code=500
        )

@mcp.custom_route("/sessions/{session_id}/notifications", methods=["GET"])
async def get_session_notifications(request: Request) -> JSONResponse:
    """SSE endpoint for session notifications"""
    from starlette.responses import StreamingResponse
    
    session_id = request.path_params["session_id"]
    
    async def event_stream():
        try:
            queue = await connection_manager.get_session_notifications(session_id)
            while True:
                try:
                    # Wait for notification with timeout
                    notification = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(notification)}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield f"data: {json.dumps({'type': 'keepalive', 'timestamp': datetime.now().isoformat()})}\n\n"
        except Exception as e:
            logger.error(f"Error in SSE stream for session {session_id}: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

@mcp.resource("sessions/{session_id}/status")
async def get_session_status(session_id: str) -> str:
    """Get connection session status"""
    try:
        session = await connection_manager.get_session(session_id)
        if not session:
            return json.dumps({"error": "Session not found"})
        
        return json.dumps({
            "session_id": session.session_id,
            "status": session.status,
            "instance_id": session.instance_id,
            "file_path": session.file_path,
            "user_id": session.user_id,
            "created_at": session.created_at.isoformat(),
            "expires_at": session.expires_at.isoformat(),
            "websocket_port": session.websocket_port
        })
    except Exception as e:
        logger.error(f"Error getting session status: {e}")
        return json.dumps({"error": str(e)})

@mcp.resource("server://info")
def server_info() -> str:
    """Get server information and status."""
    info = {
        "name": "remote-rhino-mcp-server",
        "version": "0.1.0",
        "description": "Remote MCP server for Rhino CAD integration",
        "timestamp": datetime.now().isoformat(),
        "settings": {
            "host": settings.host,
            "port": settings.port,
            "debug": settings.debug,
        },
        "active_sessions": len(connection_manager.sessions),
        "available_tools": [
            "get_rhino_scene_info",
            "get_rhino_layers", 
            "get_rhino_objects_with_metadata",
            "capture_rhino_viewport",
            "execute_rhino_code",
            "get_rhino_selected_objects",
            "look_up_RhinoScriptSyntax"
        ]
    }
    return str(info)


def main():
    """Main entry point for the server."""
    logger.info(f"Starting Remote Rhino MCP Server on {settings.host}:{settings.port}")
    logger.info("Available Rhino tools: get_rhino_scene_info, get_rhino_layers, get_rhino_objects_with_metadata, capture_rhino_viewport, execute_rhino_code, get_rhino_selected_objects, look_up_RhinoScriptSyntax")
    
    try:
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