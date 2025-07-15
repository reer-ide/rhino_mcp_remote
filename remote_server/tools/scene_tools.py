"""Scene information tools for Rhino."""
from fastmcp import Context
from typing import Optional, Dict, Any
from ._base import BaseTool
from remote_server.connection_manager import ConnectionManager


class SceneTools(BaseTool):
    """Tools for getting scene information."""
    
    async def get_rhino_scene_info(self, ctx: Context, session_id: str) -> str:
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
            result = await self.send_to_rhino(session_id, "get_rhino_scene_info")
            return self.format_json_response(result)
        except Exception as e:
            return self.handle_error("getting scene info", session_id, e)

    async def get_rhino_objects_info(self, ctx: Context, session_id: str, filters: Optional[Dict[str, Any]] = None, include_attributes: bool = False) -> str:
        """Get detailed information about objects in the scene.
        
        This function provides comprehensive object information using the standard Rhino object serialization:
        - Object ID, name, type, layer, material, color, bounding box
        - Geometry-specific information (points, lines, curves, etc.)
        - Optional description from user text
        - Optional all user attributes when include_attributes=True
        
        Available filters:
        - layer: Filter by layer name (supports wildcards, e.g., "Layer*")
        - name: Filter by object name (supports wildcards, e.g., "Cube*")
        - type: Filter by object type (e.g., "Curve", "Brep", "Point")
        - description: Filter by description text
        
        Args:
            session_id: The session ID of the connected Rhino instance
            filters: Optional dictionary of filters to apply
            include_attributes: Whether to include all user attributes in the response
        
        Returns:
            JSON string containing filtered objects with their information
        """
        try:
            params = {
                "filters": filters or {},
                "include_attributes": include_attributes
            }
            result = await self.send_to_rhino(session_id, "get_rhino_objects_info", params)
            return self.format_json_response(result)
        except Exception as e:
            return self.handle_error("getting objects info", session_id, e)


def register_tools(app, connection_manager: ConnectionManager):
    """Register scene tools with the MCP server."""
    tools = SceneTools(connection_manager)
    app.tool()(tools.get_rhino_scene_info)
    app.tool()(tools.get_rhino_objects_info) 