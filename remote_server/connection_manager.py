import asyncio
import json
import uuid
import logging
import hashlib
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import websockets
import redis.asyncio as redis
from fastmcp import FastMCP

# Import our new license management system
from remote_server.license_manager import LicenseManager, LicenseRegistration
from remote_server.utils.mock_redis import create_mock_redis

logger = logging.getLogger(__name__)

@dataclass
class PersistentSession:
    """Enhanced session model with file associations and persistence"""
    session_id: str
    user_id: str
    license_id: str
    file_path: str
    document_guid: Optional[str]  # NEW: Document GUID for file identification
    created_at: datetime
    last_active: datetime
    expires_at: datetime
    status: str = "pending"  # pending, active, dormant, expired
    instance_id: Optional[str] = None
    websocket_port: Optional[int] = None
    connection_metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.connection_metadata is None:
            self.connection_metadata = {}

class ConnectionManager:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.sessions: Dict[str, PersistentSession] = {}
        self.redis_url = redis_url
        self.redis_client = None
        self.license_manager: Optional[LicenseManager] = None
        self.use_mock_redis = False
        self.websocket_servers: Dict[int, websockets.WebSocketServer] = {}
        self.base_port = 8100  # Starting port for WebSocket connections
        self.pending_responses: Dict[str, asyncio.Future] = {}  # For correlation handling
        self.host_app_notifications: Dict[str, asyncio.Queue] = {}  # For SSE notifications
        
        # Session TTL settings
        self.session_dormant_ttl = 86400 * 30  # 30 days (same as max for simplicity)
        self.session_max_ttl = 86400 * 30      # 30 days
        
    async def _init_redis(self):
        """Initialize Redis client with fallback to mock Redis"""
        if self.redis_client is not None:
            return
        
        logger.info(f"Attempting to connect to Redis: {self.redis_url}")
        
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            # Test the connection with a short timeout
            await asyncio.wait_for(self.redis_client.ping(), timeout=5.0)
            logger.info(f"Connected to Redis successfully: {self.redis_url}")
            self.use_mock_redis = False
        except Exception as e:
            logger.warning(f"Failed to connect to Redis ({self.redis_url}): {e}")
            logger.info("Falling back to mock Redis for development")
            
            # Ensure we clean up the failed connection
            if self.redis_client:
                try:
                    await self.redis_client.close()
                except:
                    pass
            
            # Initialize mock Redis
            self.redis_client = create_mock_redis()
            self.use_mock_redis = True
            logger.info("Mock Redis initialized successfully")

    # Enhanced Session Management
    
    async def create_persistent_session(self, user_id: str, file_path: str, license_id: str) -> PersistentSession:
        """Create a new persistent session with server-generated document GUID (30-day expiration)"""
        await self._init_redis()
        
        # Validate license
        license_data = await self.license_manager.get_license(license_id)
        if not license_data or license_data.status != "active":
            raise ValueError(f"Invalid or inactive license: {license_id}")
        
        # Check concurrent session limits
        valid_sessions = await self.get_user_sessions(user_id, status_filter="active")
        if len(valid_sessions) >= license_data.max_concurrent_files:
            raise ValueError(f"Maximum concurrent sessions ({license_data.max_concurrent_files}) reached for license {license_id}")
        
        session_id = str(uuid.uuid4())
        websocket_port = await self._allocate_port()
        
        # Always generate document GUID server-side
        document_guid = str(uuid.uuid4())
        logger.info(f"Generated document GUID for session {session_id}: {document_guid}")
        
        session = PersistentSession(
            session_id=session_id,
            user_id=user_id,
            license_id=license_id,
            file_path=file_path,
            document_guid=document_guid,
            created_at=datetime.now(),
            last_active=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=self.session_max_ttl),
            websocket_port=websocket_port,
            connection_metadata={
                "created_by": "host_app",
                "license_tier": license_data.tier,
            },
            status="pending"
        )
        
        self.sessions[session_id] = session
        
        # Store in Redis with dual TTL strategy
        session_data = asdict(session)
        session_data["created_at"] = session.created_at.isoformat()
        session_data["last_active"] = session.last_active.isoformat()
        session_data["expires_at"] = session.expires_at.isoformat()
        session_data["connection_metadata"] = json.dumps(session.connection_metadata)
        
        await self.redis_client.hset(f"session:{session_id}", mapping=session_data)
        await self.redis_client.expire(f"session:{session_id}", self.session_dormant_ttl)
        
        # Add to user's session index
        await self.redis_client.sadd(f"user_sessions:{user_id}", session_id)
        await self.redis_client.expire(f"user_sessions:{user_id}", self.session_max_ttl)
        
        # Start WebSocket server for this session
        await self._start_websocket_server(session)
        
        logger.info(f"Persistent session created: {session_id} for file {file_path} (license: {license_id})")
        return session
    
    async def update_session(self, session_id: str, session: PersistentSession):
        """Update a session in Redis"""
        await self.redis_client.hset(f"session:{session_id}", mapping=asdict(session))
    
    async def get_user_sessions(self, user_id: str, status_filter: Optional[str] = None) -> List[PersistentSession]:
        """Get all sessions for a user, optionally filtered by status"""
        await self._init_redis()
        
        session_ids = await self.redis_client.smembers(f"user_sessions:{user_id}")
        sessions = []
        
        for session_id in session_ids:
            session = await self.get_session(session_id)
            if session and (not status_filter or session.status == status_filter):
                sessions.append(session)
        
        return sessions
    
    async def get_pending_sessions(self, license_id: str) -> List[PersistentSession]:
        """Get pending sessions for a license (for auto-reconnection)"""
        license_data = await self.license_manager.get_license(license_id)
        if not license_data:
            return []
        
        user_sessions = await self.get_user_sessions(license_data.user_id, status_filter="pending")
        return user_sessions
    
    async def reactivate_session(self, session_id: str) -> Optional[PersistentSession]:
        """Reactivate a dormant session"""
        session = await self.get_session(session_id)
        if not session:
            return None
        
        # Update session status and activity
        session.status = "active"
        session.last_active = datetime.now()
        
        # Update in Redis
        await self.redis_client.hset(f"session:{session_id}", mapping={
            "status": "active",
            "last_active": session.last_active.isoformat()
        })
        await self.redis_client.expire(f"session:{session_id}", self.session_dormant_ttl)
        
        # Restart WebSocket server if needed
        if session.websocket_port not in self.websocket_servers:
            await self._start_websocket_server(session)
        
        logger.info(f"Session reactivated: {session_id}")
        return session

    # File Integrity Methods

    # File integrity validation removed - now handled client-side only

    # Legacy compatibility methods (keeping existing interface)
    
    async def create_session(self, user_id: str, file_path: str) -> PersistentSession:
        """Legacy method - creates session with auto-generated license for backward compatibility"""
        # Generate a temporary license_id for legacy compatibility
        legacy_license_id = f"legacy_{user_id}_{uuid.uuid4().hex[:8]}"
        
        # Register temporary license
        machine_fingerprint = "legacy_fingerprint"  # In real implementation, get actual fingerprint
        
        # This is a bit of a hack for legacy support. We generate a dummy key.
        # In a real scenario, you might want to prevent this or handle it more gracefully.
        dummy_license_key = self.license_manager.generate_license_key(
            issued_to=user_id,
            tier="legacy",
            max_concurrent_files=1,
            validity_days=1
        ).key

        await self.license_manager.register_license(dummy_license_key, user_id, machine_fingerprint)
        
        return await self.create_persistent_session(user_id, file_path, legacy_license_id)
    
    async def _allocate_port(self) -> int:
        """Allocate an available port for WebSocket connection"""
        port = self.base_port
        while port in self.websocket_servers:
            port += 1
        return port
    
    async def _start_websocket_server(self, session: PersistentSession):
        """Start WebSocket server for a specific session"""
        async def handle_connection(websocket):
            # In websockets 15.0+, path info is available via websocket.request.path
            try:
                path = websocket.request.path
            except AttributeError:
                # Fallback for older versions
                path = getattr(websocket, 'path', '/')
            await self._handle_rhino_connection(session, websocket, path)
        
        server = await websockets.serve(
            handle_connection,
            "localhost",
            session.websocket_port
        )
        
        self.websocket_servers[session.websocket_port] = server
        logger.info(f"WebSocket server started on port {session.websocket_port} for session {session.session_id}")
    
    async def _handle_rhino_connection(self, session: PersistentSession, websocket, path):
        """Handle WebSocket connection from Rhino plugin with enhanced validation"""
        try:
            logger.info(f"New WebSocket connection for session {session.session_id}, path: {path}")
            
            # Enhanced token validation for persistent sessions
            if '?' in path:
                query_string = path.split('?')[1]
                query_params = dict(param.split('=') for param in query_string.split('&') if '=' in param)
                token = query_params.get('token')
                
                # For persistent sessions, we need to validate against the license
                license_data = await self.license_manager.get_license(session.license_id)
                if not license_data or license_data.status != "active":
                    logger.warning(f"Invalid license for session {session.session_id}")
                    await websocket.close(code=1008, reason="Invalid license")
                    return
                
                # In a real implementation, token would be derived from license_id + session_id
                # For now, we'll accept any token for backward compatibility
                
            else:
                logger.warning(f"No token provided for session {session.session_id}")
                await websocket.close(code=1008, reason="Token required")
                return
            
            # Check session expiration
            if datetime.now() > session.expires_at:
                logger.warning(f"Session {session.session_id} has expired")
                await websocket.close(code=1008, reason="Session expired")
                return
            
            # File integrity validation removed - handled client-side
            
            # Update session
            session.websocket = websocket
            session.status = "active"
            session.instance_id = str(uuid.uuid4())
            session.last_active = datetime.now()
            
            # Update Redis
            await self.redis_client.hset(
                f"session:{session.session_id}",
                mapping={
                    "status": "active",
                    "instance_id": session.instance_id,
                    "last_active": session.last_active.isoformat(),
                    "connected_at": datetime.now().isoformat()
                }
            )
            
            logger.info(f"Rhino instance connected: {session.instance_id} for session {session.session_id}")
            
            # Notify host app via SSE
            await self._notify_host_app(session, "connection_established")
            
            # Send initial handshake with enhanced metadata
            handshake = {
                "type": "handshake",
                "session_id": session.session_id,
                "instance_id": session.instance_id,
                "license_id": session.license_id,
                "file_path": session.file_path,
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send(json.dumps(handshake))
            
            # Handle messages
            async for message in websocket:
                await self._handle_rhino_message(session, message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Rhino instance disconnected: {session.instance_id}")
            session.status = "dormant"
            if hasattr(session, 'websocket'):
                session.websocket = None
            await self._notify_host_app(session, "connection_lost")
            
            # Update Redis with dormant status
            await self.redis_client.hset(
                f"session:{session.session_id}",
                mapping={
                    "status": "dormant",
                    "disconnected_at": datetime.now().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Error handling Rhino connection: {e}")
            session.status = "error"
            await self._notify_host_app(session, "connection_error")

    async def _handle_rhino_message(self, session: PersistentSession, message: str):
        """Handle messages from Rhino plugin with session context"""
        try:
            data = json.loads(message)
            message_type = data.get("type", "response")
            
            # Update session activity
            session.last_active = datetime.now()
            await self.redis_client.hset(
                f"session:{session.session_id}",
                "last_active", 
                session.last_active.isoformat()
            )
            
            if message_type == "response":
                # Handle command response
                correlation_id = data.get("correlation_id")
                if correlation_id and correlation_id in self.pending_responses:
                    future = self.pending_responses.pop(correlation_id)
                    if not future.cancelled():
                        future.set_result(data)
                else:
                    logger.warning(f"Received response with unknown correlation_id: {correlation_id}")
                    
            elif message_type == "notification":
                # Handle notifications from Rhino (e.g., file changes, errors)
                await self._notify_host_app(session, "rhino_notification", data)
                
            elif message_type == "heartbeat":
                # Handle heartbeat from Rhino plugin
                heartbeat_response = {
                    "type": "heartbeat_ack",
                    "session_id": session.session_id,
                    "timestamp": datetime.now().isoformat()
                }
                await session.websocket.send(json.dumps(heartbeat_response))
                
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in Rhino message: {e}")
        except Exception as e:
            logger.error(f"Error handling Rhino message: {e}")
    
    async def _notify_host_app(self, session: PersistentSession, event_type: str, data: Optional[Dict] = None):
        """Notify host app via SSE about connection events"""
        notification = {
            "type": event_type,
            "session_id": session.session_id,
            "instance_id": session.instance_id or "unknown",
            "license_id": session.license_id,
            "file_path": session.file_path,
            "timestamp": datetime.now().isoformat(),
            "data": data or {}
        }
        
        # Add to notification queue for this session
        if session.session_id not in self.host_app_notifications:
            self.host_app_notifications[session.session_id] = asyncio.Queue()
        
        await self.host_app_notifications[session.session_id].put(notification)
        logger.info(f"Notification queued for session {session.session_id}: {event_type}")
    
    async def send_to_rhino(self, session_id: str, tool: str, params: Optional[Dict[str, Any]] = None, timeout: float = 120.0) -> dict:
        """Send a command to a Rhino instance and wait for a response."""
        session = self.sessions.get(session_id)
        if not session or not session.websocket:
            raise ValueError(f"No active connection for session {session_id}")

        # File integrity validation removed - handled client-side

        # Prepare command message
        correlation_id = str(uuid.uuid4())
        message = {
            "type": "command",
            "tool": tool,
            "params": params or {},
            "correlation_id": correlation_id,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }

        # Create future for response
        future = asyncio.Future()
        self.pending_responses[correlation_id] = future
        
        try:
            # Send message to Rhino
            await session.websocket.send(json.dumps(message))
            logger.info(f"Sent command to Rhino {session.instance_id}: {tool}")
            
            # Wait for response with timeout
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
            
        except asyncio.TimeoutError:
            # Clean up pending response
            self.pending_responses.pop(correlation_id, None)
            raise TimeoutError(f"Timeout waiting for response from Rhino instance {session.instance_id}")
        except websockets.exceptions.ConnectionClosed:
            # Clean up pending response
            self.pending_responses.pop(correlation_id, None)
            raise ConnectionError(f"Connection to Rhino instance {session.instance_id} was closed")
        except Exception as e:
            # Clean up pending response
            self.pending_responses.pop(correlation_id, None)
            raise e

    async def get_session(self, session_id: str) -> Optional[PersistentSession]:
        """Get session by ID with Redis fallback"""
        # Try memory first
        if session_id in self.sessions:
            return self.sessions[session_id]
        
        # Try Redis
        await self._init_redis()
        session_data = await self.redis_client.hgetall(f"session:{session_id}")
        if not session_data:
            return None
        
        # Reconstruct session object
        session = PersistentSession(
            session_id=session_id,
            user_id=session_data["user_id"],
            license_id=session_data["license_id"],
            file_path=session_data["file_path"],
            document_guid=session_data.get("document_guid"),
            created_at=datetime.fromisoformat(session_data["created_at"]),
            last_active=datetime.fromisoformat(session_data["last_active"]),
            expires_at=datetime.fromisoformat(session_data["expires_at"]),
            status=session_data.get("status", "pending"),
            instance_id=session_data.get("instance_id"),
            websocket_port=int(session_data["websocket_port"]) if session_data.get("websocket_port") else None,
            connection_metadata=json.loads(session_data.get("connection_metadata", "{}"))
        )
        
        # Cache in memory
        self.sessions[session_id] = session
        return session
    
    async def get_session_notifications(self, session_id: str) -> asyncio.Queue:
        """Get notification queue for a session"""
        if session_id not in self.host_app_notifications:
            self.host_app_notifications[session_id] = asyncio.Queue()
        return self.host_app_notifications[session_id]
    
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions with enhanced lifecycle management (30-day expiration)"""
        current_time = datetime.now()
        expired_sessions = []
        dormant_sessions = []
        
        # Check all sessions for expiration
        all_session_keys = await self.redis_client.keys("session:*")
        for key in all_session_keys:
            session_id = key.replace("session:", "")
            session = await self.get_session(session_id)
            
            if not session:
                continue
            
            if current_time > session.expires_at:
                expired_sessions.append(session_id)
            elif session.status == "active" and (current_time - session.last_active).seconds > self.session_dormant_ttl:
                dormant_sessions.append(session_id)
        
        # Clean up expired sessions
        for session_id in expired_sessions:
            await self._cleanup_session(session_id)
        
        # Mark dormant sessions
        for session_id in dormant_sessions:
            await self._mark_session_dormant(session_id)
        
        logger.info(f"Cleanup completed: {len(expired_sessions)} expired, {len(dormant_sessions)} marked dormant")
    
    async def _mark_session_dormant(self, session_id: str):
        """Mark a session as dormant but don't delete it"""
        session = await self.get_session(session_id)
        if session:
            session.status = "dormant"
            await self.redis_client.hset(f"session:{session_id}", "status", "dormant")
            
            # Close WebSocket connection if active
            if session.websocket:
                await session.websocket.close()
                session.websocket = None
            
            logger.info(f"Session marked as dormant: {session_id}")
    
    async def _expire_session(self, session_id: str, reason: str = "expired"):
        """Expire a session due to various reasons"""
        session = await self.get_session(session_id)
        if session:
            session.status = "expired"
            await self.redis_client.hset(f"session:{session_id}", mapping={
                "status": "expired",
                "expired_reason": reason,
                "expired_at": datetime.now().isoformat()
            })
            
            await self._notify_host_app(session, "session_expired", {"reason": reason})
            logger.info(f"Session expired: {session_id}, reason: {reason}")
    
    async def _cleanup_session(self, session_id: str):
        """Clean up a specific session completely"""
        session = self.sessions.pop(session_id, None)
        if session:
            # Close WebSocket connection if active
            if session.websocket:
                await session.websocket.close()
            
            # Stop WebSocket server
            if session.websocket_port and session.websocket_port in self.websocket_servers:
                server = self.websocket_servers.pop(session.websocket_port)
                server.close()
                await server.wait_closed()
            
            # Clean up Redis data
            await self.redis_client.delete(f"session:{session_id}")
            await self.redis_client.srem(f"user_sessions:{session.user_id}", session_id)
            
            # Clean up notification queue
            self.host_app_notifications.pop(session_id, None)
            
            logger.info(f"Cleaned up session {session_id}")
    
    async def close(self):
        """Close connection manager and clean up resources"""
        # Close all WebSocket servers
        for server in self.websocket_servers.values():
            server.close()
            await server.wait_closed()
        
        # Close Redis connection
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("Connection manager closed")