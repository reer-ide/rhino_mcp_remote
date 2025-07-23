"""
Dependency injection for Remote Rhino MCP Server.
"""

import asyncio
from typing import Optional
from fastmcp.utilities.logging import get_logger

from remote_server.connection_manager import ConnectionManager
from remote_server.license_manager import LicenseManager
from remote_server.config import settings

logger = get_logger(__name__)

# Global managers - will be initialized lazily
_connection_manager: Optional[ConnectionManager] = None
_license_manager: Optional[LicenseManager] = None
_initialization_lock: Optional[asyncio.Lock] = None
_managers_initialized = False


async def initialize_managers():
    """Initialize the managers with separate Redis connections"""
    global _connection_manager, _license_manager, _managers_initialized, _initialization_lock
    
    # Create lock if it doesn't exist
    if _initialization_lock is None:
        _initialization_lock = asyncio.Lock()
    
    async with _initialization_lock:
        # Check if already initialized (double-checked locking pattern)
        if _managers_initialized:
            return
            
        logger.info("Starting manager initialization...")
        
        # Initialize connection manager with its own Redis
        _connection_manager = ConnectionManager(redis_url=settings.redis_connection_url)
        await _connection_manager._init_redis()
        logger.info("ConnectionManager Redis initialized")
        
        # Initialize license manager with its own Redis connection
        _license_manager = LicenseManager(redis_url=settings.redis_connection_url)
        await _license_manager._init_redis()
        logger.info("LicenseManager Redis initialized")
        
        # Give connection manager access to license manager for session validation
        _connection_manager.license_manager = _license_manager
        
        _managers_initialized = True


async def ensure_managers_initialized():
    """Ensure managers are initialized, initializing them if needed"""
    if not _managers_initialized:
        await initialize_managers()


async def get_connection_manager() -> ConnectionManager:
    """Get the connection manager instance."""
    await ensure_managers_initialized()
    if _connection_manager is None:
        raise RuntimeError("Connection manager not initialized")
    return _connection_manager


async def get_license_manager() -> LicenseManager:
    """Get the license manager instance."""
    await ensure_managers_initialized()
    if _license_manager is None:
        raise RuntimeError("License manager not initialized")
    return _license_manager


def get_app_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance for tools (sync version)."""
    if _connection_manager is None:
        raise RuntimeError("Connection manager not initialized")
    return _connection_manager