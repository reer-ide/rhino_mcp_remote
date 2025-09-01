"""Layer management tools for Rhino."""
from fastmcp import Context
from typing import List, Dict, Any, Optional
from remote_server.connection_manager import ConnectionManager
from remote_server.utils.tool_helpers import handle_tool_exe_response, handle_error


def register_tools(mcp, connection_manager: Optional[ConnectionManager]):
    """Register layer tools with the MCP server."""
    
    @mcp.tool()
    async def create_rhino_layers(session_id: str, layers: List[Dict[str, Any]] = None, name: str = None, color: List[int] = None, parent: str = None) -> str:
        """Create layers in Rhino document.
        
        Args:
            session_id: The session ID of the connected Rhino instance
            layers: List of layer definitions to create, each containing:
                - name: Layer name (required)
                - color: RGB color array [r, g, b] (optional)
                - parent: Parent layer name (optional)
            name: Single layer name (alternative to layers list)
            color: RGB color for single layer [r, g, b]
            parent: Parent layer name for single layer
            
        Returns:
            JSON string with structure:
            {
              "status": "success",
              "count": 1,
              "layers": [
                {
                  "status": "success",
                  "id": "layer-guid",
                  "name": "Layer Name",
                  "color": {"r": 255, "g": 0, "b": 0},
                  "parent": "parent-layer-guid"
                }
              ]
            }
            
            On error:
            {
              "error": "Error message"
            }
        """
        try:
            params = {}
            
            if layers:
                params["layers"] = layers
            else:
                if name:
                    params["name"] = name
                if color:
                    params["color"] = color
                if parent:
                    params["parent"] = parent
                      
            # Get connection manager lazily
            from remote_server.dependencies import get_connection_manager
            conn_mgr = await get_connection_manager()
            
            result = await conn_mgr.send_to_rhino(session_id, "create_rhino_layers", params)
            return handle_tool_exe_response("creating layers", session_id, result)
        except Exception as e:
            return handle_error("creating layers", session_id, e)

    @mcp.tool()
    async def delete_rhino_layers(session_id: str, layers: List[Dict[str, Any]] = None, name: str = None, guid: str = None, force: bool = False) -> str:
        """Delete layers from Rhino document.
        
        Args:
            session_id: The session ID of the connected Rhino instance
            layers: List of layer definitions to delete, each containing:
                - name: Layer name (optional if guid provided)
                - guid: Layer GUID (optional if name provided)
                - force: Force deletion even if layer contains objects (optional)
            name: Single layer name to delete (alternative to layers list)
            guid: Single layer GUID to delete (alternative to layers list)
            force: Force deletion even if layer contains objects
            
        Returns:
            JSON string with structure:
            {
              "status": "success",
              "count": 1,
              "layers": [
                {
                  "status": "success",
                  "name": "Layer Name",
                  "id": "layer-guid",
                  "objects_deleted": 5,
                  "message": "Layer 'Layer Name' deleted successfully"
                }
              ]
            }
            
            On error:
            {
              "error": "Error message"
            }
        """
        try:
            params = {}
            
            if layers:
                params["layers"] = layers
            else:
                if name:
                    params["name"] = name
                if guid:
                    params["guid"] = guid
                if force:
                    params["force"] = force
                      
            # Get connection manager lazily
            from remote_server.dependencies import get_connection_manager
            conn_mgr = await get_connection_manager()
            
            result = await conn_mgr.send_to_rhino(session_id, "delete_rhino_layers", params)
            return handle_tool_exe_response("deleting layers", session_id, result)
        except Exception as e:
            return handle_error("deleting layers", session_id, e)

