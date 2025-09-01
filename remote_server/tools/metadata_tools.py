"""Metadata management tools for Rhino objects."""
from fastmcp import Context
from typing import List, Optional, Dict, Any
from remote_server.connection_manager import ConnectionManager
from remote_server.utils.tool_helpers import handle_tool_exe_response, handle_error


def register_tools(mcp, connection_manager: Optional[ConnectionManager]):
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
            JSON string with structure:
            {
              "status": "success",
              "objects_processed": 2,
              "results": [
                {
                  "object_id": "guid-string",
                  "status": "success",
                  "name": "Object Name",
                  "description": "Object description"
                },
                {
                  "object_id": "guid-string-2",
                  "status": "error",
                  "error": "Object not found"
                }
              ]
            }
            
            On error:
            {
              "error": "Error message"
            }
        """
        try:
            params = {
                "object_ids": object_ids,
                "name": name,
                "description": description
            }
            # Get connection manager lazily
            from remote_server.dependencies import get_connection_manager
            conn_mgr = await get_connection_manager()
            
            result = await conn_mgr.send_to_rhino(session_id, "add_rhino_objects_metadata", params)
            return handle_tool_exe_response("adding metadata to objects", session_id, result)
        except Exception as e:
            return handle_error("adding metadata to objects", session_id, e)

    @mcp.tool()
    async def update_rhino_objects_metadata(session_id: str, object_ids: List[str], name: Optional[str] = None, description: Optional[str] = None) -> str:
        """Update metadata on Rhino objects.
        
        Args:
            session_id: The session ID of the connected Rhino instance
            object_ids: List of object IDs to update metadata on
            name: Optional new name for objects
            description: Optional new description for objects
            
        Returns:
            JSON string with structure:
            {
              "status": "success",
              "objects_processed": 2,
              "results": [
                {
                  "object_id": "guid-string",
                  "status": "success",
                  "name": "Updated Object Name",
                  "description": "Updated description"
                },
                {
                  "object_id": "guid-string-2",
                  "status": "error",
                  "error": "Failed to modify object attributes"
                }
              ]
            }
            
            On error:
            {
              "error": "Error message"
            }
        """
        try:
            params = {
                "object_ids": object_ids,
                "name": name,
                "description": description
            }
            # Get connection manager lazily
            from remote_server.dependencies import get_connection_manager
            conn_mgr = await get_connection_manager()
            
            result = await conn_mgr.send_to_rhino(session_id, "update_rhino_objects_metadata", params)
            return handle_tool_exe_response("updating metadata for objects", session_id, result)
        except Exception as e:
            return handle_error("updating metadata for objects", session_id, e)
