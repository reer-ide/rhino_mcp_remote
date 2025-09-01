"""Scene information tools for Rhino."""
from fastmcp import Context
from typing import Optional, Dict, Any, List
from remote_server.connection_manager import ConnectionManager
from remote_server.utils.tool_helpers import handle_tool_exe_response, handle_error


def register_tools(mcp, connection_manager: Optional[ConnectionManager]):
    """Register scene tools with the MCP server."""
    
    @mcp.tool()
    async def get_rhino_scene_info(session_id: str) -> str:
        """Get basic information about the current Rhino scene.
        
        This is a lightweight function that returns basic scene information:
        - Document metadata (name, dates, tolerances, units, object/layer counts)
        - List of all layers with basic information and up to 5 sample objects per layer
        - Object samples include: id, name, type, color, material, and any user metadata
        - Use this for quick scene overview or when you only need basic object information
        
        Args:
            session_id: The session ID of the connected Rhino instance
            
        Returns dict with: status, selected_count, unique_objects_count, selected_objects (array)
        Sample response:
            {
              "status": "success",
              "document": {
                "name": "document_name.3dm",
                "date_created": "2024-01-01T12:00:00Z",
                "date_modified": "2024-01-01T13:30:00Z",
                "tolerance": 0.01,
                "angle_tolerance": 1.0,
                "units": "Millimeters",
                "total_objects": 25,
                "total_layers": 5
              },
              "layers": [
                {
                  "id": "layer-guid",
                  "name": "Layer 01",
                  "full_path": "Layer 01", 
                  "color": "#FF0000",
                  "visible": true,
                  "locked": false,
                  "object_count": 12,
                  "sample_objects": [
                    {
                      "id": "object-guid",
                      "name": "Object Name",
                      "type": "Curve",
                      "color": "#0000FF", 
                      "material": "Default",
                      "user_data": {"key": "value"}
                    }
                  ]
                }
              ],
              "timestamp": "2024-01-01T14:00:00Z"
            }
        """
        try:
            # Get connection manager lazily
            from remote_server.dependencies import get_connection_manager
            conn_mgr = await get_connection_manager()
            result = await conn_mgr.send_to_rhino(session_id, "get_rhino_scene_info")
            return handle_tool_exe_response("getting scene info", session_id, result)
        except Exception as e:
            return handle_error("getting scene info", session_id, e)

    @mcp.tool()
    async def get_rhino_objects_info(session_id: str, obj_guids: Optional[List[str]] = None, get_all_objects: bool = False, include_attributes: bool = False) -> str:
        """Get detailed information about specific objects by their GUIDs, or all objects in the document.
        
        This function provides comprehensive object information including:
        - GUID, name, type, layer, color, bounding box
        - All user-defined metadata from the objects
        - Complete object attributes and metadata (if include_attributes is True)
        - Proper material information using RenderMaterial (not MaterialIndex)
        
        IMPORTANT: Using get_all_objects=True may return a very large amount of data if the document 
        contains many objects. Use this option carefully and consider using obj_guids for specific objects instead.
        
        Args:
            session_id: The session ID of the connected Rhino instance
            obj_guids: Optional list of object GUIDs to get information for specific objects
            get_all_objects: If True, returns information for ALL objects in the document (use with caution - may return large amounts of data)
            include_attributes: Whether to include full object attributes in the response (default: False for performance)
            
        Returns:
            JSON string with structure:
            {
              "status": "success",
              "objects": [
                {
                  "object_id": "guid-string",
                  "name": "Object Name",
                  "geometry_type": "Curve",
                  "layer": {
                    "id": "layer-guid",
                    "name": "Layer 01",
                    "full_path": "Parent::Layer 01"
                  },
                  "color": "#FF0000",
                  "material": "Material Name",
                  "visible": true,
                  "locked": false,
                  "user_data": {"key": "value"},
                  "bounding_box": {
                    "min": [0, 0, 0],
                    "max": [10, 10, 10]
                  },
                  "attributes": {...} // if include_attributes=True
                }
              ],
              "count": 5,
              "get_all_objects": false,
              "timestamp": "2024-01-01T14:00:00Z"
            }
        """
        try:
            if not obj_guids and not get_all_objects:
                raise Exception("Either 'obj_guids' list or 'get_all_objects' = True must be provided")
            
            # Get connection manager lazily
            from remote_server.dependencies import get_connection_manager
            conn_mgr = await get_connection_manager()
            
            params = {
                "obj_guids": obj_guids,
                "get_all_objects": get_all_objects,
                "include_attributes": include_attributes
            }
            result = await conn_mgr.send_to_rhino(session_id, "get_rhino_objects_info", params)
            return handle_tool_exe_response("getting objects info", session_id, result)
        except Exception as e:
            return handle_error("getting objects info", session_id, e)










