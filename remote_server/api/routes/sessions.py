"""
Session management endpoints for Remote Rhino MCP Server.
"""

import asyncio
import json
from datetime import datetime
from fastmcp import FastMCP
from fastmcp.utilities.logging import get_logger
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse

from remote_server.dependencies import get_connection_manager
from remote_server.config import settings

logger = get_logger(__name__)


def register_session_routes(mcp: FastMCP):
    """Register session management routes with the FastMCP server."""
    
    @mcp.custom_route("/sessions/create", methods=["POST"])
    async def create_session(request: Request) -> JSONResponse:
        """Create a new persistent session with client-provided file information"""
        try:
            connection_manager = await get_connection_manager()
                
            data = await request.json()
            user_id = data.get("user_id") 
            file_path = data.get("file_path")
            license_id = data.get("license_id")
            document_guid = data.get("document_guid")
            
            if not user_id or not file_path:
                return JSONResponse(
                    {"error": "user_id and file_path are required"}, 
                    status_code=400
                )
            
            # Choose session creation method based on whether license_id is provided
            if license_id:
                session = await connection_manager.create_persistent_session(
                    user_id, file_path, license_id, document_guid
                )
            else:
                # Legacy compatibility - create session without explicit license
                session = await connection_manager.create_session(user_id, file_path)
            
            # Use 127.0.0.1 for client connections instead of 0.0.0.0 bind address
            client_host = "127.0.0.1" if settings.host == "0.0.0.0" else settings.host
            
            return JSONResponse({
                "session_id": session.session_id,
                "instance_id": session.instance_id,  # Will be None initially, set when WebSocket connects
                "license_id": session.license_id,
                "websocket_port": session.websocket_port,
                "websocket_url": f"ws://{client_host}:{session.websocket_port}?session_id={session.session_id}",
                "file_path": session.file_path,
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

    @mcp.custom_route("/sessions/{user_id}", methods=["GET"])
    async def get_user_sessions(request: Request) -> JSONResponse:
        """Get all sessions for a user"""
        try:
            connection_manager = await get_connection_manager()
            user_id = request.path_params.get("user_id")
            
            if not user_id:
                return JSONResponse(
                    {"error": "user_id query parameter is required"},
                    status_code=400
                )
            
            sessions = await connection_manager.get_user_sessions(user_id)
            
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
                "valid_sessions": session_data,
                "total_count": len(session_data)
            })
            
        except Exception as e:
            logger.error(f"Error getting user sessions: {e}")
            return JSONResponse(
                {"error": "Failed to get user sessions"}, 
                status_code=500
            )

    @mcp.custom_route("/sessions/pending", methods=["GET"])
    async def get_pending_sessions(request: Request) -> JSONResponse:
        """Get pending sessions for a license (for auto-reconnection)"""
        try:
            connection_manager = await get_connection_manager()
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

    @mcp.custom_route("/sessions/connect", methods=["POST"])
    async def connect_to_session(request: Request) -> JSONResponse:
        """Connect plugin to an existing session created by host app"""
        try:
            connection_manager = await get_connection_manager()
            data = await request.json()
            user_id = data.get("user_id")
            file_path = data.get("file_path")
            license_id = data.get("license_id")
            document_guid = data.get("document_guid")
            
            if not user_id or not license_id:
                return JSONResponse(
                    {"error": "user_id and license_id are required"}, 
                    status_code=400
                )
            
            # Find session by GUID first, then fall back to file path
            user_sessions = await connection_manager.get_user_sessions(user_id)
            matching_session = None
            
            # Primary matching: GUID + license_id
            if document_guid:
                for session in user_sessions:
                    if (session.document_guid == document_guid and 
                        session.license_id == license_id and
                        session.status in ["pending", "active"]):
                        matching_session = session
                        # Update file path if changed
                        if file_path and session.file_path != file_path:
                            session.file_path = file_path
                            await connection_manager.redis_client.hset(
                                f"session:{session.session_id}", 
                                "file_path", file_path
                            )
                            logger.info(f"Updated file path for session {session.session_id}: {file_path}")
                        break
            
            # Fallback matching: file_path + license_id (for legacy support)
            if not matching_session and file_path:
                normalized_path = file_path.replace("\\", "/")
                for session in user_sessions:
                    session_file_path = session.file_path.replace("\\", "/")
                    if (session_file_path == normalized_path and 
                        session.license_id == license_id and
                        session.status in ["pending", "active"] and
                        not session.document_guid):  # Only match sessions without GUID
                        matching_session = session
                        break
            
            if not matching_session:
                error_msg = "No matching session found. Session must be created by host application first."
                if document_guid:
                    error_msg += f" (Searched by document GUID: {document_guid})"
                elif file_path:
                    error_msg += f" (Searched by file path: {file_path})"
                return JSONResponse(
                    {"error": error_msg}, 
                    status_code=404
                )
            
            # Check if session is expired
            if datetime.now() > matching_session.expires_at:
                return JSONResponse(
                    {"error": "Session has expired"}, 
                    status_code=410
                )
            
            # Reactivate the session for connection
            session = await connection_manager.reactivate_session(matching_session.session_id)
            
            if not session:
                return JSONResponse(
                    {"error": "Failed to activate session for connection"}, 
                    status_code=500
                )
            
            # Use 127.0.0.1 for client connections
            client_host = "127.0.0.1" if settings.host == "0.0.0.0" else settings.host
            
            logger.info(f"Plugin connected to existing session {session.session_id} for file {file_path}")
            
            return JSONResponse({
                "session_id": session.session_id,
                "instance_id": session.instance_id,
                "websocket_url": f"ws://{client_host}:{session.websocket_port}?session_id={session.session_id}",
                "file_path": session.file_path,
                "status": session.status,
                "connected_at": datetime.now().isoformat(),
                "expires_at": session.expires_at.isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error connecting to session: {e}")
            return JSONResponse(
                {"error": "Failed to connect to session"}, 
                status_code=500
            )

    @mcp.custom_route("/sessions/reconnect", methods=["POST"])
    async def reconnect_session(request: Request) -> JSONResponse:
        """Reconnect to an existing session (for client session persistence)"""
        try:
            connection_manager = await get_connection_manager()
            data = await request.json()
            session_id = data.get("session_id")
            license_id = data.get("license_id")
            user_id = data.get("user_id")
            
            if not session_id or not license_id or not user_id:
                return JSONResponse(
                    {"error": "session_id, license_id, and user_id are required"}, 
                    status_code=400
                )
            
            # Get the session
            session = await connection_manager.get_session(session_id)
            
            if not session:
                return JSONResponse(
                    {"error": "Session not found"}, 
                    status_code=404
                )
            
            # Validate license and user match
            if session.license_id != license_id or session.user_id != user_id:
                return JSONResponse(
                    {"error": "License ID or user ID mismatch"}, 
                    status_code=403
                )
            
            # Check if session is expired
            if datetime.now() > session.expires_at:
                return JSONResponse(
                    {"error": "Session has expired"}, 
                    status_code=410
                )
            
            # Reactivate the session
            session = await connection_manager.reactivate_session(session_id)
            
            if not session:
                return JSONResponse(
                    {"error": "Failed to reactivate session"}, 
                    status_code=500
                )
            
            # Use 127.0.0.1 for client connections
            client_host = "127.0.0.1" if settings.host == "0.0.0.0" else settings.host
            
            return JSONResponse({
                "session_id": session.session_id,
                "instance_id": session.instance_id,
                "websocket_url": f"ws://{client_host}:{session.websocket_port}?session_id={session.session_id}",
                "file_path": session.file_path,
                "status": session.status,
                "reconnected_at": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error reconnecting to session: {e}")
            return JSONResponse(
                {"error": "Failed to reconnect to session"}, 
                status_code=500
            )

    @mcp.custom_route("/sessions/{session_id}/reactivate", methods=["POST"])
    async def reactivate_session(request: Request) -> JSONResponse:
        """Reactivate a dormant session"""
        try:
            connection_manager = await get_connection_manager()
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
        connection_manager = await get_connection_manager()
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
            connection_manager = await get_connection_manager()
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