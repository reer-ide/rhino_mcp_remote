"""
Main FastMCP server for Remote Rhino CAD integration.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

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
        "version": "0.1.0",
        "architecture": "persistent_sessions_with_licensing"
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

# License Registration Endpoints

@mcp.custom_route("/license/register", methods=["POST"])
async def register_license(request: Request) -> JSONResponse:
    """Register a license using a license key"""
    try:
        data = await request.json()
        license_key = data.get("license_key")
        user_id = data.get("user_id")
        machine_fingerprint = data.get("machine_fingerprint")
        
        if not license_key or not user_id or not machine_fingerprint:
            return JSONResponse(
                {"error": "license_key, user_id, and machine_fingerprint are required"},
                status_code=400
            )
        
        license_registration = await connection_manager.register_license(
            license_key, user_id, machine_fingerprint
        )
        
        return JSONResponse({
            "status": "success",
            "license_id": license_registration.license_id,
            "user_id": license_registration.user_id,
            "tier": license_registration.tier,
            "registered_at": license_registration.registered_at.isoformat(),
            "max_concurrent_files": license_registration.max_concurrent_files
        })
        
    except ValueError as e:
        return JSONResponse(
            {"error": str(e)}, 
            status_code=400
        )
    except Exception as e:
        logger.error(f"Error registering license: {e}")
        return JSONResponse(
            {"error": f"Failed to register license: {str(e)}"}, 
            status_code=500
        )

@mcp.custom_route("/license/validate", methods=["POST"])
async def validate_license(request: Request) -> JSONResponse:
    """Validate a license key or license ID with machine fingerprint"""
    try:
        data = await request.json()
        license_key = data.get("license_key")
        license_id = data.get("license_id")
        machine_fingerprint = data.get("machine_fingerprint")
        
        if not machine_fingerprint:
            return JSONResponse(
                {"error": "machine_fingerprint is required"},
                status_code=400
            )
        
        if license_key:
            # Validate using license key
            is_valid, validation_license_id = await connection_manager.validate_license_key(
                license_key, machine_fingerprint
            )
            if is_valid:
                license_data = await connection_manager.get_license(validation_license_id)
                return JSONResponse({
                    "status": "valid",
                    "license_id": validation_license_id,
                    "user_id": license_data.user_id if license_data else None,
                    "tier": license_data.tier if license_data else None,
                    "last_seen": license_data.last_seen.isoformat() if license_data else None
                })
            else:
                return JSONResponse({
                    "status": "invalid",
                    "message": "Invalid license key or machine fingerprint mismatch"
                }, status_code=401)
                
        elif license_id:
            # Validate using license ID (legacy method)
            is_valid = await connection_manager.validate_license(license_id, machine_fingerprint)
            if is_valid:
                license_data = await connection_manager.get_license(license_id)
                return JSONResponse({
                    "status": "valid",
                    "license_id": license_id,
                    "user_id": license_data.user_id if license_data else None,
                    "tier": license_data.tier if license_data else None,
                    "last_seen": license_data.last_seen.isoformat() if license_data else None
                })
            else:
                return JSONResponse({
                    "status": "invalid",
                    "message": "License not found or machine fingerprint mismatch"
                }, status_code=401)
        else:
            return JSONResponse(
                {"error": "Either license_key or license_id is required"},
                status_code=400
            )
        
    except Exception as e:
        logger.error(f"Error validating license: {e}")
        return JSONResponse(
            {"error": "Failed to validate license"}, 
            status_code=500
        )

@mcp.custom_route("/license/{license_id}/info", methods=["GET"])
async def get_license_info(request: Request) -> JSONResponse:
    """Get license information"""
    try:
        license_id = request.path_params["license_id"]
        license_data = await connection_manager.get_license(license_id)
        
        if not license_data:
            return JSONResponse(
                {"error": "License not found"}, 
                status_code=404
            )
        
        return JSONResponse({
            "license_id": license_data.license_id,
            "user_id": license_data.user_id,
            "status": license_data.status,
            "tier": license_data.tier,
            "registered_at": license_data.registered_at.isoformat(),
            "last_seen": license_data.last_seen.isoformat(),
            "max_concurrent_files": license_data.max_concurrent_files
        })
        
    except Exception as e:
        logger.error(f"Error getting license info: {e}")
        return JSONResponse(
            {"error": "Failed to get license info"}, 
            status_code=500
        )

@mcp.custom_route("/license/generate", methods=["POST"])
async def generate_license_key(request: Request) -> JSONResponse:
    """Generate a new license key (for testing/admin purposes)"""
    try:
        data = await request.json()
        issued_to = data.get("issued_to")
        tier = data.get("tier", "beta")
        validity_days = data.get("validity_days", 90)
        max_concurrent_files = data.get("max_concurrent_files", 3)
        
        if not issued_to:
            return JSONResponse(
                {"error": "issued_to is required"},
                status_code=400
            )
        
        # Generate license key
        license_key = connection_manager.license_manager.generate_license_key(
            issued_to=issued_to,
            tier=tier,
            max_concurrent_files=max_concurrent_files,
            validity_days=validity_days
        )
        
        return JSONResponse({
            "license_id": license_key.license_id,
            "license_key": license_key.key,
            "issued_to": license_key.issued_to,
            "tier": license_key.tier,
            "max_concurrent_files": license_key.max_concurrent_files,
            "issued_at": license_key.issued_at.isoformat(),
            "expires_at": license_key.expires_at.isoformat() if license_key.expires_at else None,
            "features": license_key.features
        })
        
    except Exception as e:
        logger.error(f"Error generating license key: {e}")
        return JSONResponse(
            {"error": f"Failed to generate license key: {str(e)}"}, 
            status_code=500
        )

# Enhanced Session Management Endpoints

@mcp.custom_route("/sessions/create", methods=["POST"])
async def create_session(request: Request) -> JSONResponse:
    """Create a new persistent session with client-provided file information"""
    try:
        data = await request.json()
        user_id = data.get("user_id") 
        file_path = data.get("file_path")
        license_id = data.get("license_id")
        file_hash = data.get("file_hash")  # Client-provided file hash
        file_size = data.get("file_size", 0)  # Client-provided file size
        
        if not user_id or not file_path:
            return JSONResponse(
                {"error": "user_id and file_path are required"}, 
                status_code=400
            )
        
        # Choose session creation method based on whether license_id is provided
        if license_id:
            session = await connection_manager.create_persistent_session(
                user_id, file_path, license_id, file_hash, file_size
            )
        else:
            # Legacy compatibility - create session without explicit license
            session = await connection_manager.create_session(user_id, file_path)
        
        # Use 127.0.0.1 for client connections instead of 0.0.0.0 bind address
        client_host = "127.0.0.1" if settings.host == "0.0.0.0" else settings.host
        
        return JSONResponse({
            "session_id": session.session_id,
            "license_id": session.license_id,
            "websocket_port": session.websocket_port,
            "websocket_url": f"ws://{client_host}:{session.websocket_port}?session_id={session.session_id}",
            "file_path": session.file_path,
            "file_hash": session.file_hash,
            "status": session.status,
            "created_at": session.created_at.isoformat(),
            "expires_at": session.expires_at.isoformat()
        })
        
    except ValueError as e:
        # Handle license validation or session limit errors
        return JSONResponse(
            {"error": str(e)}, 
            status_code=400
        )
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        return JSONResponse(
            {"error": "Failed to create session"}, 
            status_code=500
        )

@mcp.custom_route("/sessions/active", methods=["GET"])
async def get_active_sessions(request: Request) -> JSONResponse:
    """Get active sessions for a user"""
    try:
        user_id = request.query_params.get("user_id")
        license_id = request.query_params.get("license_id")
        
        if not user_id:
            return JSONResponse(
                {"error": "user_id query parameter is required"},
                status_code=400
            )
        
        sessions = await connection_manager.get_user_sessions(user_id)
        
        # Filter by license if specified
        if license_id:
            sessions = [s for s in sessions if s.license_id == license_id]
        
        session_data = []
        for session in sessions:
            session_data.append({
                "session_id": session.session_id,
                "license_id": session.license_id,
                "file_path": session.file_path,
                "status": session.status,
                "instance_id": session.instance_id,
                "created_at": session.created_at.isoformat(),
                "last_active": session.last_active.isoformat(),
                "websocket_port": session.websocket_port
            })
        
        return JSONResponse({
            "user_id": user_id,
            "active_sessions": session_data,
            "total_count": len(session_data)
        })
        
    except Exception as e:
        logger.error(f"Error getting active sessions: {e}")
        return JSONResponse(
            {"error": "Failed to get active sessions"}, 
            status_code=500
        )

@mcp.custom_route("/sessions/pending", methods=["GET"])
async def get_pending_sessions(request: Request) -> JSONResponse:
    """Get pending sessions for a license (for auto-reconnection)"""
    try:
        license_id = request.query_params.get("license_id")
        
        if not license_id:
            return JSONResponse(
                {"error": "license_id query parameter is required"},
                status_code=400
            )
        
        sessions = await connection_manager.get_pending_sessions(license_id)
        
        session_data = []
        for session in sessions:
            session_data.append({
                "session_id": session.session_id,
                "file_path": session.file_path,
                "file_hash": session.file_hash,
                "created_at": session.created_at.isoformat(),
                "websocket_port": session.websocket_port
            })
        
        return JSONResponse({
            "license_id": license_id,
            "pending_sessions": session_data,
            "count": len(session_data)
        })
        
    except Exception as e:
        logger.error(f"Error getting pending sessions: {e}")
        return JSONResponse(
            {"error": "Failed to get pending sessions"}, 
            status_code=500
        )

@mcp.custom_route("/sessions/{session_id}/reactivate", methods=["POST"])
async def reactivate_session(request: Request) -> JSONResponse:
    """Reactivate a dormant session"""
    try:
        session_id = request.path_params["session_id"]
        session = await connection_manager.reactivate_session(session_id)
        
        if not session:
            return JSONResponse(
                {"error": "Session not found"}, 
                status_code=404
            )
        
        # Use 127.0.0.1 for client connections
        client_host = "127.0.0.1" if settings.host == "0.0.0.0" else settings.host
        
        return JSONResponse({
            "session_id": session.session_id,
            "status": session.status,
            "websocket_url": f"ws://{client_host}:{session.websocket_port}?session_id={session.session_id}",
            "file_path": session.file_path,
            "reactivated_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error reactivating session: {e}")
        return JSONResponse(
            {"error": "Failed to reactivate session"}, 
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

@mcp.custom_route("/sessions/{session_id}/status", methods=["GET"])
async def get_session_status(request: Request) -> JSONResponse:
    """Get detailed session status"""
    try:
        session_id = request.path_params["session_id"]
        session = await connection_manager.get_session(session_id)
        
        if not session:
            return JSONResponse(
                {"error": "Session not found"}, 
                status_code=404
            )
        
        return JSONResponse({
            "session_id": session.session_id,
            "user_id": session.user_id,
            "license_id": session.license_id,
            "status": session.status,
            "instance_id": session.instance_id,
            "file_path": session.file_path,
            "file_hash": session.file_hash,
            "created_at": session.created_at.isoformat(),
            "last_active": session.last_active.isoformat(),
            "expires_at": session.expires_at.isoformat(),
            "websocket_port": session.websocket_port,
            "connection_metadata": session.connection_metadata
        })
        
    except Exception as e:
        logger.error(f"Error getting session status: {e}")
        return JSONResponse(
            {"error": "Failed to get session status"}, 
            status_code=500
        )

# Legacy Compatibility Route (kept for backward compatibility)
@mcp.custom_route("/sessions/create_legacy", methods=["POST"])
async def create_session_legacy(request: Request) -> JSONResponse:
    """Legacy session creation endpoint (for backward compatibility)"""
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
            "connection_token": "legacy_token",  # For backward compatibility
            "websocket_port": session.websocket_port,
            "websocket_url": f"ws://{client_host}:{session.websocket_port}?token=legacy_token",
            "expires_at": session.expires_at.isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error creating legacy session: {e}")
        return JSONResponse(
            {"error": "Failed to create session"}, 
            status_code=500
        )

@mcp.resource("sessions/{session_id}/status")
async def get_session_status_resource(session_id: str) -> str:
    """Get connection session status as MCP resource"""
    try:
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
        "active_sessions": len(connection_manager.sessions),
        "active_licenses": len(connection_manager.licenses),
        "features": [
            "license_registration",
            "persistent_sessions", 
            "auto_reconnection",
            "file_integrity_validation",
            "enhanced_session_lifecycle"
        ],
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
    logger.info(f"Starting Remote Rhino MCP Server v2.0 on {settings.host}:{settings.port}")
    logger.info("Architecture: License-based persistent sessions with auto-reconnection")
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