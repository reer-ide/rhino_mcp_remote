"""Object selection tools for Rhino."""
from fastmcp import Context
from typing import Dict, Any, Optional
from remote_server.connection_manager import ConnectionManager
from remote_server.utils.tool_helpers import handle_tool_exe_response, handle_error


def register_tools(mcp, connection_manager: Optional[ConnectionManager]):
    """Register selection tools with the MCP server."""
    
    @mcp.tool()
    async def get_rhino_selected_objects(session_id: str, include_lights: bool = False, include_grips: bool = False) -> str:
        """Get the info of all objects that are currently selected in Rhino.
        
        Returns information about all selected objects including their Guid, metadata,
        geometry type, layer information, and user-defined data. Supports both full object
        and subobject selection (faces, edges, etc.).
        
        Args:
            session_id: The session ID of the connected Rhino instance
            include_lights: Whether to include light objects in selection (default: False)
            include_grips: Whether to include grip objects in selection (default: False)
            
        Returns dict with: status, selected_count, unique_objects_count, selected_objects (array)
        - selected_count: Total number of selections (including subobjects)
        - unique_objects_count: Number of unique parent objects
        
        Sample response (full object selection):
            {
              "status": "success",
              "selected_count": 5,
              "unique_objects_count": 3,
              "include_lights": false,
              "include_grips": false,
              "selected_objects": [
                {
                  "id": "guid-string",
                  "type": "Curve",
                  "name": "Object Name",
                  "layer": "Layer 01",
                  "metadata": {"key": "value"},
                  "selection_type": "full"
                }
              ]
            }
            
        Sample response (subobject selection):
            {
              "status": "success",
              "selected_count": 3,
              "unique_objects_count": 1,
              "include_lights": false,
              "include_grips": false,
              "selected_objects": [
                {
                  "id": "guid-string",
                  "type": "Brep",
                  "name": "Object Name",
                  "layer": "Layer 01",
                  "metadata": {"key": "value"},
                  "selection_type": "subobject", // or "mixed" if both the parent object and its subobjects selected
                  "subobjects": [
                    {
                      "index": 0,
                      "type": "BrepFace"
                    },
                    {
                      "index": 2,
                      "type": "BrepFace"
                    }
                  ]
                }
              ]
            }
            
            If no objects selected:
            {
              "error": "No objects selected"
            }
        """
        try:
            params = {
                "include_lights": include_lights,
                "include_grips": include_grips
            }
            # Get connection manager lazily
            from remote_server.dependencies import get_connection_manager
            conn_mgr = await get_connection_manager()
            
            result = await conn_mgr.send_to_rhino(session_id, "get_rhino_selected_objects", params)
            return handle_tool_exe_response("getting selected objects", session_id, result)
        except Exception as e:
            return handle_error("getting selected objects", session_id, e)

    @mcp.tool()
    async def select_filtered_rhino_objects(session_id: str, filters: Dict[str, Any] = {}, filters_type: str = "and") -> str:
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
        - Example: {"structural_type": "beam"} searches for objects with custom attribute "structural_type" = "beam"
        
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
            JSON string with structure:
            {
              "status": "success", 
              "selected_count": 3,
              "selected_objects": ["guid-1", "guid-2", "guid-3"],
              "unselectable_count": 1,
              "unselectable_objects": ["guid-4"],
              "message": "Selected 3 objects, 1 object could not be selected"
            }
        """
        try:
            params = {
                "filters": filters,
                "filters_type": filters_type
            }
            # Get connection manager lazily
            from remote_server.dependencies import get_connection_manager
            conn_mgr = await get_connection_manager()
            
            result = await conn_mgr.send_to_rhino(session_id, "select_filtered_rhino_objects", params)
            return handle_tool_exe_response("selecting objects", session_id, result)
        except Exception as e:
            return handle_error("selecting objects", session_id, e)








