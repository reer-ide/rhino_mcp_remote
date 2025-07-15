"""Layer management tools for Rhino."""
from fastmcp import Context
from typing import List, Dict, Any, Optional
from ._base import BaseTool
from remote_server.connection_manager import ConnectionManager


class LayerTools(BaseTool):
    """Tools for managing Rhino layers."""
    
    async def create_rhino_layers(self, ctx: Context, session_id: str, layers: List[Dict[str, Any]] = None, name: str = None, color: List[int] = None, parent: str = None) -> str:
        """Create layers in Rhino document.
        
        Args:
            session_id: The session ID of the connected Rhino instance
            layers: List of layer definitions with name, color, and parent properties (new format)
            name: Layer name (single layer format for backward compatibility)
            color: RGB color array [R, G, B] for layer color (single layer format)
            parent: Parent layer name (single layer format)
            
        Layer definition format:
            {
                "name": "layer_name",           # Optional - if omitted, Rhino generates name
                "color": [255, 0, 0],          # Optional RGB array [0-255, 0-255, 0-255]
                "parent": "parent_layer_name"   # Optional parent layer name
            }
            
        Examples:
            # Multiple layers
            layers = [
                {"name": "Architecture", "color": [255, 0, 0]},
                {"name": "Structure", "color": [0, 255, 0], "parent": "Architecture"}
            ]
            
            # Single layer (backward compatibility)
            name = "New Layer", color = [255, 0, 0], parent = "Default"
            
        Returns:
            JSON string containing created layer information and status
        """
        try:
            params = {}
            
            if layers is not None:
                params["layers"] = layers
            else:
                # Single layer format for backward compatibility
                if name is not None:
                    params["name"] = name
                if color is not None:
                    params["color"] = color
                if parent is not None:
                    params["parent"] = parent
                    
            result = await self.send_to_rhino(session_id, "create_rhino_layers", params)
            return self.format_json_response(result)
        except Exception as e:
            return self.handle_error("creating layers", session_id, e)

    async def delete_rhino_layers(self, ctx: Context, session_id: str, layers: List[Dict[str, Any]] = None, name: str = None, guid: str = None, force: bool = False) -> str:
        """Delete layers from Rhino document.
        
        Args:
            session_id: The session ID of the connected Rhino instance
            layers: List of layer identifiers with name, guid, and options (new format)
            name: Layer name to delete (single layer format for backward compatibility)
            guid: Layer GUID to delete (single layer format for backward compatibility)
            force: Force delete layer and all objects on it (single layer format)
            
        Layer deletion format:
            {
                "name": "layer_name",     # Either name or guid required
                "guid": "layer-guid",     # Either name or guid required
                "force": false,           # Optional - delete objects on layer if true
                "quiet": true             # Optional - suppress warnings during deletion
            }
            
        Note:
            - Cannot delete default layer (layer 0)
            - Cannot delete layer with child layers
            - Use force=true to delete layer with objects
            
        Examples:
            # Multiple layers
            layers = [
                {"name": "Architecture", "force": true},
                {"guid": "layer-guid-here"}
            ]
            
            # Single layer (backward compatibility)
            name = "Layer to Delete", force = true
            
        Returns:
            JSON string containing deletion results and status
        """
        try:
            params = {}
            
            if layers is not None:
                params["layers"] = layers
            else:
                # Single layer format for backward compatibility
                if name is not None:
                    params["name"] = name
                if guid is not None:
                    params["guid"] = guid
                if force:
                    params["force"] = force
                    
            result = await self.send_to_rhino(session_id, "delete_rhino_layers", params)
            return self.format_json_response(result)
        except Exception as e:
            return self.handle_error("deleting layers", session_id, e)


def register_tools(app, connection_manager: ConnectionManager):
    """Register layer tools with the MCP server."""
    tools = LayerTools(connection_manager)
    app.tool()(tools.create_rhino_layers)
    app.tool()(tools.delete_rhino_layers) 