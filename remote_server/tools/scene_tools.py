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
        - List of all layers with basic information about the layer and 5 sample objects with their metadata 
        - No metadata or detailed properties
        - Use this for quick scene overview or when you only need basic object information
        
        Args:
            session_id: The session ID of the connected Rhino instance
            
        Returns:
            JSON string containing basic scene information
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
        - GUID
        - Name
        - Type
        - Layer
        - Color
        - Bounding Box
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
            JSON string containing objects information with proper material data and metadata
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










