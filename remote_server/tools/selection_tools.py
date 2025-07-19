"""Object selection tools for Rhino."""
import json
import logging
from fastmcp import Context
from typing import Dict, Any, Optional
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
    """Register selection tools with the MCP server."""
    
    @mcp.tool()
    async def get_rhino_selected_objects(session_id: str, include_lights: bool = False, include_grips: bool = False) -> str:
        """Get the identifiers of all objects that are currently selected in Rhino.
        
        Args:
            session_id: The session ID of the connected Rhino instance
            include_lights: Whether to include light objects in selection (default: False)
            include_grips: Whether to include grip objects in selection (default: False)
            
        Returns:
            JSON string containing list of selected object IDs and their basic information
        """
        try:
            params = {
                "include_lights": include_lights,
                "include_grips": include_grips
            }
            result = await connection_manager.send_to_rhino(session_id, "get_rhino_selected_objects", params)
            return _format_json_response(result)
        except Exception as e:
            return _handle_error("getting selected objects", session_id, e)

    @mcp.tool()
    async def select_rhino_objects(session_id: str, filters: Dict[str, Any] = {}, filters_type: str = "and") -> str:
        """Select Rhino objects based on filters.
        
        Args:
            session_id: The session ID of the connected Rhino instance
            filters: Dictionary containing selection criteria
            filters_type: How to combine multiple filters ("and" or "or", default: "and")
            
        Returns:
            JSON string containing selection results and count of selected objects
        """
        try:
            params = {
                "filters": filters,
                "filters_type": filters_type
            }
            result = await connection_manager.send_to_rhino(session_id, "select_rhino_objects", params)
            return _format_json_response(result)
        except Exception as e:
            return _handle_error("selecting objects", session_id, e)








