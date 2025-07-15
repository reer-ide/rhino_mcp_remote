"""Metadata management tools for Rhino objects."""
from fastmcp import Context
from typing import List, Optional
from ._base import BaseTool
from remote_server.connection_manager import ConnectionManager


class MetadataTools(BaseTool):
    """Tools for managing object metadata."""
    
    async def add_rhino_objects_metadata(self, ctx: Context, session_id: str, object_ids: List[str], name: Optional[str] = None, description: Optional[str] = None) -> str:
        """Add name and description to Rhino objects.
        
        Args:
            session_id: The session ID of the connected Rhino instance
            object_ids: List of object IDs to add metadata to
            name: Optional name for the objects
            description: Optional description for the objects
            
        Returns:
            JSON string containing the metadata operation results
        """
        try:
            params = {
                "object_ids": object_ids,
                "name": name,
                "description": description
            }
            result = await self.send_to_rhino(session_id, "add_rhino_objects_metadata", params)
            return self.format_json_response(result)
        except Exception as e:
            return self.handle_error("adding metadata to objects", session_id, e)

    async def update_rhino_objects_metadata(self, ctx: Context, session_id: str, object_ids: List[str], name: Optional[str] = None, description: Optional[str] = None) -> str:
        """Update name and description of Rhino objects.
        
        Args:
            session_id: The session ID of the connected Rhino instance
            object_ids: List of object IDs to update metadata for
            name: Optional new name for the objects
            description: Optional new description for the objects
            
        Returns:
            JSON string containing the metadata operation results
        """
        try:
            params = {
                "object_ids": object_ids,
                "name": name,
                "description": description
            }
            result = await self.send_to_rhino(session_id, "update_rhino_objects_metadata", params)
            return self.format_json_response(result)
        except Exception as e:
            return self.handle_error("updating metadata for objects", session_id, e)


def register_tools(app, connection_manager: ConnectionManager):
    """Register metadata tools with the MCP server."""
    tools = MetadataTools(connection_manager)
    app.tool()(tools.add_rhino_objects_metadata)
    app.tool()(tools.update_rhino_objects_metadata) 