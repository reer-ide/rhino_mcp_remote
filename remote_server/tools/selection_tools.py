"""Object selection tools for Rhino."""
from fastmcp import Context
from typing import Dict, Any, Optional
from remote_server.connection_manager import ConnectionManager
from remote_server.utils.tool_helpers import handle_tool_exe_response, handle_error


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
            return handle_tool_exe_response("getting selected objects", session_id, result)
        except Exception as e:
            return handle_error("getting selected objects", session_id, e)

    @mcp.tool()
    async def select_rhino_objects(session_id: str, filters: Dict[str, Any] = {}, filters_type: str = "and") -> str:
        """Select Rhino objects based on various filters.

        This tool supports filtering objects by multiple criteria:
        
        Built-in filters:
        - "name": Object name (string or list of strings)
        - "layer": Layer name (string or list of strings)
        - "color": Object color as [R, G, B] array or list of color arrays
        - "material": Material ID from RenderMaterial.Id (string or list of strings)
          - Use "layer_default" or "default" to select objects using layer default material
          - Use actual material IDs to select objects with specific materials
        
        Custom attribute filters:
        - Any other filter name will search in user-defined metadata/attributes
        - Example: {"geometry_type": "Point"} searches for objects with custom attribute "geometry_type" = "Point"
        
        Args:
            session_id: The session ID of the connected Rhino instance
            filters: Dictionary containing selection criteria. Examples:
                - {"name": "Wall_01"} - Select object named "Wall_01"
                - {"layer": ["Construction", "Reference"]} - Select objects on Construction or Reference layers
                - {"material": "layer_default"} - Select objects using layer default material
                - {"material": ["material-id-1", "material-id-2"]} - Select objects with specific materials
                - {"color": [255, 0, 0]} - Select red objects
                - {"custom_type": "beam"} - Select objects with custom attribute "custom_type" = "beam"
            filters_type: How to combine multiple filters ("and" or "or", default: "and")
            
        Returns:
            JSON string containing selection results, count and GUIDs of selected objects, and any unselectable objects
        """
        try:
            params = {
                "filters": filters,
                "filters_type": filters_type
            }
            result = await connection_manager.send_to_rhino(session_id, "select_rhino_objects", params)
            return handle_tool_exe_response("selecting objects", session_id, result)
        except Exception as e:
            return handle_error("selecting objects", session_id, e)








