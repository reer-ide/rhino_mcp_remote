"""Scene information tools for Rhino."""
import json
import logging
from fastmcp import Context
from typing import Optional, Dict, Any
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
    """Register scene tools with the MCP server."""
    
    @mcp.tool()
    async def get_rhino_scene_info(session_id: str) -> str:
        """Get basic information about the current Rhino scene.
        
        This is a lightweight function that returns basic scene information:
        - List of all layers with basic information about the layer and 5 sample objects with their metadata 
        - No metadata or detailed properties
        - Use this for quick scene overview or when you only need basic object information
        
        Args:
            session_id: The session ID of the connected Rhino instance
            
        Returns:
            JSON string containing basic scene information
        """
        try:
            result = await connection_manager.send_to_rhino(session_id, "get_rhino_scene_info")
            return _format_json_response(result)
        except Exception as e:
            return _handle_error("getting scene info", session_id, e)

    @mcp.tool()
    async def get_rhino_objects_info(session_id: str, filters: Optional[Dict[str, Any]] = None, include_attributes: bool = False) -> str:
        """Get detailed information about objects in the scene.
        
        This function provides comprehensive object information including:
        - Full geometry details and properties
        - Complete object attributes and metadata
        - Filtering capabilities for specific object types
        - Use this when you need detailed analysis or when working with specific object properties
        
        Args:
            session_id: The session ID of the connected Rhino instance
            filters: Optional dictionary to filter objects (e.g., {"type": "curve", "layer": "Construction"})
            include_attributes: Whether to include full object attributes in the response (default: False for performance)
            
        Returns:
            JSON string containing filtered objects with their information
        """
        try:
            params = {
                "filters": filters or {},
                "include_attributes": include_attributes
            }
            result = await connection_manager.send_to_rhino(session_id, "get_rhino_objects_info", params)
            return _format_json_response(result)
        except Exception as e:
            return _handle_error("getting objects info", session_id, e)










