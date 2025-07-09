import asyncio
import json
import uuid
import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import websockets
import redis.asyncio as redis
from fastmcp import FastMCP

logger = logging.getLogger(__name__)

# Import mock Redis for fallback
from remote_server.utils.mock_redis import create_mock_redis

@dataclass
class ConnectionSession:
    session_id: str
    user_id: str
    file_path: str
    connection_token: str
    websocket_port: int
    created_at: datetime
    expires_at: datetime
    status: str = "pending"  # pending, connected, disconnected
    instance_id: Optional[str] = None
    websocket: Optional[websockets.WebSocketServerProtocol] = None

class ConnectionManager:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.sessions: Dict[str, ConnectionSession] = {}
        self.redis_url = redis_url
        self.redis_client = None
        self.use_mock_redis = False
        self.websocket_servers: Dict[int, websockets.WebSocketServer] = {}
        self.base_port = 8100  # Starting port for WebSocket connections
        self.pending_responses: Dict[str, asyncio.Future] = {}  # For correlation handling
        self.host_app_notifications: Dict[str, asyncio.Queue] = {}  # For SSE notifications
        
    async def _init_redis(self):
        """Initialize Redis client with fallback to mock Redis"""
        if self.redis_client is not None:
            return
            
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            # Test the connection
            await self.redis_client.ping()
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}")
            logger.info("Using mock Redis for development")
            self.redis_client = create_mock_redis()
            self.use_mock_redis = True
        
    async def create_session(self, user_id: str, file_path: str) -> ConnectionSession:
        """Create a new connection session"""
        await self._init_redis()  # Initialize Redis if not already done
        
        session_id = str(uuid.uuid4())
        connection_token = str(uuid.uuid4())
        websocket_port = await self._allocate_port()
        
        session = ConnectionSession(
            session_id=session_id,
            user_id=user_id,
            file_path=file_path,
            connection_token=connection_token,
            websocket_port=websocket_port,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(minutes=10)  # 10 min to connect
        )
        
        self.sessions[session_id] = session
        
        # Store in Redis for persistence
        session_data = {
            "user_id": user_id,
            "file_path": file_path,
            "connection_token": connection_token,
            "websocket_port": str(websocket_port),
            "status": "pending",
            "created_at": session.created_at.isoformat(),
            "expires_at": session.expires_at.isoformat()
        }
        await self.redis_client.hset(f"session:{session_id}", mapping=session_data)
        await self.redis_client.expire(f"session:{session_id}", 3600)  # 1 hour TTL
        
        # Start WebSocket server for this session
        await self._start_websocket_server(session)
        
        return session
    
    async def _allocate_port(self) -> int:
        """Allocate an available port for WebSocket connection"""
        port = self.base_port
        while port in self.websocket_servers:
            port += 1
        return port
    
    async def _start_websocket_server(self, session: ConnectionSession):
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
            "0.0.0.0",
            session.websocket_port
        )
        
        self.websocket_servers[session.websocket_port] = server
        print(f"WebSocket server started on port {session.websocket_port} for session {session.session_id}")
    
    async def _handle_rhino_connection(self, session: ConnectionSession, websocket, path):
        """Handle WebSocket connection from Rhino plugin"""
        try:
            logger.info(f"New WebSocket connection for session {session.session_id}, path: {path}")
            
            # Validate connection token
            if '?' in path:
                query_string = path.split('?')[1]
                query_params = dict(param.split('=') for param in query_string.split('&') if '=' in param)
                token = query_params.get('token')
                
                logger.info(f"Received token: {token}, Expected: {session.connection_token}")
                
                if token != session.connection_token:
                    logger.warning(f"Invalid token for session {session.session_id}")
                    await websocket.close(code=1008, reason="Invalid token")
                    return
            else:
                logger.warning(f"No token provided for session {session.session_id}")
                await websocket.close(code=1008, reason="Token required")
                return
            
            # Check session expiration
            logger.info(f"Checking session expiration for {session.session_id}")
            if datetime.now() > session.expires_at:
                logger.warning(f"Session {session.session_id} has expired")
                await websocket.close(code=1008, reason="Session expired")
                return
            
            # Update session
            logger.info(f"Updating session {session.session_id}")
            session.websocket = websocket
            session.status = "connected"
            session.instance_id = str(uuid.uuid4())
            
            # Update Redis
            logger.info(f"Updating Redis for session {session.session_id}")
            try:
                await self.redis_client.hset(
                    f"session:{session.session_id}",
                    mapping={
                        "status": "connected",
                        "instance_id": session.instance_id,
                        "connected_at": datetime.now().isoformat()
                    }
                )
                logger.info(f"Redis update successful for session {session.session_id}")
            except Exception as e:
                logger.error(f"Redis update failed for session {session.session_id}: {e}")
            
            logger.info(f"Rhino instance connected: {session.instance_id} for session {session.session_id}")
            
            # Notify host app via SSE
            logger.info(f"Notifying host app for session {session.session_id}")
            try:
                await self._notify_host_app(session, "connection_established")
                logger.info(f"Host app notification successful for session {session.session_id}")
            except Exception as e:
                logger.error(f"Host app notification failed for session {session.session_id}: {e}")
            
            # Send initial handshake
            logger.info(f"Sending handshake for session {session.session_id}")
            handshake = {
                "type": "handshake",
                "session_id": session.session_id,
                "instance_id": session.instance_id,
                "timestamp": datetime.now().isoformat()
            }
            try:
                await websocket.send(json.dumps(handshake))
                logger.info(f"Handshake sent successfully for session {session.session_id}")
            except Exception as e:
                logger.error(f"Failed to send handshake for session {session.session_id}: {e}")
                raise
            
            # Handle messages
            async for message in websocket:
                await self._handle_rhino_message(session, message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Rhino instance disconnected: {session.instance_id}")
            session.status = "disconnected"
            session.websocket = None
            await self._notify_host_app(session, "connection_lost")
            
            # Update Redis
            await self.redis_client.hset(
                f"session:{session.session_id}",
                mapping={
                    "status": "disconnected",
                    "disconnected_at": datetime.now().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Error handling Rhino connection: {e}")
            session.status = "error"
            await self._notify_host_app(session, "connection_error")
    
    async def _handle_rhino_message(self, session: ConnectionSession, message: str):
        """Handle messages from Rhino plugin"""
        try:
            data = json.loads(message)
            message_type = data.get("type", "response")
            
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
                    "timestamp": datetime.now().isoformat()
                }
                await session.websocket.send(json.dumps(heartbeat_response))
                
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in Rhino message: {e}")
        except Exception as e:
            logger.error(f"Error handling Rhino message: {e}")
    
    async def _notify_host_app(self, session: ConnectionSession, event_type: str, data: Optional[Dict] = None):
        """Notify host app via SSE about connection events"""
        notification = {
            "type": event_type,
            "session_id": session.session_id,
            "instance_id": session.instance_id or "unknown",
            "timestamp": datetime.now().isoformat(),
            "data": data or {}
        }
        
        # Add to notification queue for this session
        if session.session_id not in self.host_app_notifications:
            self.host_app_notifications[session.session_id] = asyncio.Queue()
        
        await self.host_app_notifications[session.session_id].put(notification)
        logger.info(f"Notification queued for session {session.session_id}: {event_type}")
    
    async def send_to_rhino(self, session_id: str, tool: str, params: Optional[Dict[str, Any]] = None, timeout: float = 30.0) -> dict:
        """Send a command to a Rhino instance and wait for a response."""
        session = self.sessions.get(session_id)
        if not session or not session.websocket:
            raise ValueError(f"No active connection for session {session_id}")

        # Prepare command message
        correlation_id = str(uuid.uuid4())
        message = {
            "type": "command",
            "tool": tool,
            "params": params or {},
            "correlation_id": correlation_id,
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

    async def get_session(self, session_id: str) -> Optional[ConnectionSession]:
        """Get session by ID"""
        return self.sessions.get(session_id)
    
    async def get_session_notifications(self, session_id: str) -> asyncio.Queue:
        """Get notification queue for a session"""
        if session_id not in self.host_app_notifications:
            self.host_app_notifications[session_id] = asyncio.Queue()
        return self.host_app_notifications[session_id]
    
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        current_time = datetime.now()
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if current_time > session.expires_at:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            await self._cleanup_session(session_id)
    
    async def _cleanup_session(self, session_id: str):
        """Clean up a specific session"""
        session = self.sessions.pop(session_id, None)
        if session:
            # Close WebSocket connection if active
            if session.websocket:
                await session.websocket.close()
            
            # Stop WebSocket server
            if session.websocket_port in self.websocket_servers:
                server = self.websocket_servers.pop(session.websocket_port)
                server.close()
                await server.wait_closed()
            
            # Clean up Redis data
            await self.redis_client.delete(f"session:{session_id}")
            
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
        await self.redis_client.close()
        
        logger.info("Connection manager closed")