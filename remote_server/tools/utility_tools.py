"""Utility tools for basic server operations."""
import json
import logging
from fastmcp import Context
from typing import Optional, Dict, Any
try:
    from ..connection_manager import ConnectionManager
except ImportError:
    from remote_server.connection_manager import ConnectionManager

logger = logging.getLogger("RhinoTools")

def _format_json_response(result: Dict[str, Any]) -> str:
    """Format a result dictionary as a JSON string."""
    return json.dumps(result, indent=2)


def _handle_error(operation: str, session_id: str, error: Exception) -> str:
    """Handle and log errors consistently."""
    error_msg = f"Error {operation} in session {session_id}: {str(error)}"
    logger.error(error_msg)
    return error_msg


def register_tools(mcp, connection_manager: ConnectionManager):
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
            result = await connection_manager.send_to_rhino(session_id, "ping")
            return _format_json_response(result)
        except Exception as e:
            return _handle_error("pinging Rhino", session_id, e)