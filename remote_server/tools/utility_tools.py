"""Utility tools for basic server operations."""
from fastmcp import Context
from typing import Optional, Dict, Any
try:
    from ..connection_manager import ConnectionManager
except ImportError:
    from remote_server.connection_manager import ConnectionManager
from remote_server.utils.tool_helpers import handle_tool_exe_response, handle_error


def register_tools(mcp, connection_manager: Optional[ConnectionManager]):
    """Register utility tools with the MCP server."""
    
    @mcp.tool()
    async def ping(session_id: str) -> str:
        """Ping the Rhino session to check if it is connected.
        
        Args:
            session_id: The session ID of the connected Rhino instance
            
        Returns:
            JSON string containing the ping response
        """
        try:
            # Get connection manager lazily
            from remote_server.dependencies import get_connection_manager
            conn_mgr = await get_connection_manager()
            
            result = await conn_mgr.send_to_rhino(session_id, "ping")
            return handle_tool_exe_response("pinging Rhino", session_id, result)
        except Exception as e:
            return handle_error("pinging Rhino", session_id, e)