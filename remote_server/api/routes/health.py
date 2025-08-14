"""
Health check and debug endpoints for Remote Rhino MCP Server.
"""

from datetime import datetime
from fastmcp import FastMCP
from fastmcp.utilities.logging import get_logger
from starlette.requests import Request
from starlette.responses import JSONResponse

from remote_server.dependencies import get_connection_manager, get_license_manager

logger = get_logger(__name__)


def register_health_routes(mcp: FastMCP):
    """Register health and debug routes with the FastMCP server."""
    
    @mcp.custom_route("/health", methods=["GET"])
    async def health_check(request: Request) -> JSONResponse:
        """Health check endpoint for load balancers and monitoring."""
        # Ensure managers are initialized on first health check
        from remote_server.dependencies import initialize_managers
        try:
            await initialize_managers()
        except Exception as e:
            logger.warning(f"Manager initialization during health check: {e}")
        
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
            connection_manager = await get_connection_manager()
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

    # Debug Endpoints
    @mcp.custom_route("/debug/mock-redis", methods=["GET"])
    async def get_mock_redis_status(request: Request) -> JSONResponse:
        """Get mock Redis data summary (development only)"""
        try:
            connection_manager = await get_connection_manager()
            license_manager = await get_license_manager()
                
            if not connection_manager.use_mock_redis and not license_manager.use_mock_redis:
                return JSONResponse(
                    {"error": "Not using mock Redis"}, 
                    status_code=400
                )
            
            # Get data summary from both separate instances
            connection_summary = connection_manager.redis_client.get_data_summary() if connection_manager.use_mock_redis else None
            license_summary = license_manager.redis_client.get_data_summary() if license_manager.use_mock_redis else None
            
            return JSONResponse({
                "status": "success",
                "using_mock_redis": True,
                "connection_manager": {
                    "uses_mock": connection_manager.use_mock_redis,
                    "data_summary": connection_summary
                },
                "license_manager": {
                    "uses_mock": license_manager.use_mock_redis,
                    "data_summary": license_summary
                },
                "active_sessions_count": len(connection_manager.sessions),
                "active_sessions_list": list(connection_manager.sessions.keys()),
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error getting mock Redis status: {e}")
            return JSONResponse(
                {"error": "Failed to get mock Redis status"}, 
                status_code=500
            )

    @mcp.custom_route("/debug/mock-redis/clear", methods=["POST"])
    async def clear_mock_redis_data(request: Request) -> JSONResponse:
        """Clear all mock Redis data (development only)"""
        try:
            connection_manager = await get_connection_manager()
            license_manager = await get_license_manager()
            
            if not connection_manager.use_mock_redis and not license_manager.use_mock_redis:
                return JSONResponse(
                    {"error": "Not using mock Redis"}, 
                    status_code=400
                )
            
            # Get summary before clearing from both instances
            connection_summary_before = connection_manager.redis_client.get_data_summary() if connection_manager.use_mock_redis else None
            license_summary_before = license_manager.redis_client.get_data_summary() if license_manager.use_mock_redis else None
            
            # Clear data from both separate instances
            if connection_manager.use_mock_redis:
                connection_manager.redis_client.clear_all_data()
                # Clear manager caches
                connection_manager.sessions.clear()
                connection_manager.host_app_notifications.clear()
            
            if license_manager.use_mock_redis:
                license_manager.redis_client.clear_all_data()
            
            return JSONResponse({
                "status": "success",
                "message": "Separate mock Redis instances cleared",
                "data_cleared": {
                    "connection_manager": connection_summary_before,
                    "license_manager": license_summary_before
                },
                "managers_cleared": {
                    "connection_manager_sessions": "cleared" if connection_manager.use_mock_redis else "not_using_mock",
                    "connection_manager_notifications": "cleared" if connection_manager.use_mock_redis else "not_using_mock",
                    "license_manager_data": "cleared" if license_manager.use_mock_redis else "not_using_mock"
                },
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error clearing mock Redis data: {e}")
            return JSONResponse(
                {"error": "Failed to clear mock Redis data"}, 
                status_code=500
            )