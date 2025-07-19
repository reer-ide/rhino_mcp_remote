"""Metadata management tools for Rhino objects."""
import json
import logging
from fastmcp import Context
from typing import List, Optional, Dict, Any
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
    """Register metadata tools with the MCP server."""
    
    @mcp.tool()
    async def add_rhino_objects_metadata(session_id: str, object_ids: List[str], name: Optional[str] = None, description: Optional[str] = None) -> str:
        """Add metadata to Rhino objects.
        
        Args:
            session_id: The session ID of the connected Rhino instance
            object_ids: List of object IDs to add metadata to
            name: Optional name to add to objects
            description: Optional description to add to objects
            
        Returns:
            JSON string containing metadata addition results
        """
        try:
            params = {
                "object_ids": object_ids,
                "name": name,
                "description": description
            }
            result = await connection_manager.send_to_rhino(session_id, "add_rhino_objects_metadata", params)
            return _format_json_response(result)
        except Exception as e:
            return _handle_error("adding metadata to objects", session_id, e)

    @mcp.tool()
    async def update_rhino_objects_metadata(session_id: str, object_ids: List[str], name: Optional[str] = None, description: Optional[str] = None) -> str:
        """Update metadata on Rhino objects.
        
        Args:
            session_id: The session ID of the connected Rhino instance
            object_ids: List of object IDs to update metadata on
            name: Optional new name for objects
            description: Optional new description for objects
            
        Returns:
            JSON string containing metadata update results
        """
        try:
            params = {
                "object_ids": object_ids,
                "name": name,
                "description": description
            }
            result = await connection_manager.send_to_rhino(session_id, "update_rhino_objects_metadata", params)
            return _format_json_response(result)
        except Exception as e:
            return _handle_error("updating metadata for objects", session_id, e)
