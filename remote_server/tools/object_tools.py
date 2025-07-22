"""Object creation, modification, and deletion tools for Rhino."""
from fastmcp import Context
from typing import List, Dict, Any, Optional
from remote_server.connection_manager import ConnectionManager
from remote_server.utils.tool_helpers import handle_tool_exe_response, handle_error


def register_tools(mcp, connection_manager: ConnectionManager):
    """Register object tools with the MCP server."""
    
    @mcp.tool()
    async def create_rhino_basic_objects(session_id: str, objects: List[Dict[str, Any]]) -> str:
        """Create multiple basic geometry objects in Rhino at once
        
        This function efficiently creates multiple geometric objects in a single operation.
        Each object must specify its type and required parameters.
        
        Supported object types and their parameters:
        
        - POINT: Create a point
          Parameters: point [x,y,z]
        
        - LINE: Create a line segment  
          Parameters: start [x,y,z], end [x,y,z]
        
        - POLYLINE: Create a polyline through points
          Parameters: points [[x,y,z], [x,y,z], ...]
        
        - CIRCLE: Create a circle
          Parameters: center [x,y,z], radius
        
        - ARC: Create an arc
          Parameters: center [x,y,z], radius, start_angle (degrees), end_angle (degrees)
        
        - RECTANGLE: Create a rectangle 
          Parameters: corner1 [x,y,z], corner2 [x,y,z] OR center [x,y,z], width, height
        
        - BOX: Create a box/cuboid
          Parameters: center [x,y,z], width, length, height
        
        - SPHERE: Create a sphere
          Parameters: center [x,y,z], radius
        
        - CONE: Create a cone
          Parameters: center [x,y,z], radius, height, cap (optional, default true)
        
        - CYLINDER: Create a cylinder
          Parameters: center [x,y,z], radius, height, cap (optional, default true)
        
        - SURFACE: Create a NURBS surface
          Parameters: points [[x,y,z], ...], count [u,v], degree [u,v] (optional), closed [u,v] (optional)
        
        Args:
            session_id: The session ID of the connected Rhino instance
            objects: List of objects to create, each containing:
                - type: REQUIRED geometry type (e.g., "box", "sphere", "cylinder")
                - name: REQUIRED name for the object (for easier identification)
                - params: REQUIRED dictionary of geometry-specific parameters
        
        Returns:
            JSON string containing the IDs and details of created objects
        """
        try:
            params = {
                "objects": objects
            }
            result = await connection_manager.send_to_rhino(session_id, "create_rhino_basic_geometries", params)
            return handle_tool_exe_response("creating basic geometries", session_id, result)
        except Exception as e:
            return handle_error("creating basic geometries", session_id, e)

    @mcp.tool()
    async def delete_rhino_objects(session_id: str, objects: List[Dict[str, Any]] = None, id: str = None, name: str = None, all: bool = False) -> str:
        """Delete objects from Rhino document.
        
        This function can delete objects by various criteria:
        - Specific objects by providing a list with IDs/names
        - Single object by ID or name  
        - All objects in the document (use with caution)
        
        Args:
            session_id: The session ID of the connected Rhino instance
            objects: List of objects to delete, each containing either "id" or "name"
            id: Single object ID to delete (alternative to objects list)
            name: Single object name to delete (alternative to objects list)  
            all: If true, deletes ALL objects in the document (use with extreme caution)
        
        Returns:
            JSON string containing deletion results and count of deleted objects
        """
        try:
            params = {}
            
            if all:
                params["all"] = True
            elif objects:
                params["objects"] = objects
            elif id:
                params["id"] = id
            elif name:
                params["name"] = name
                  
            result = await connection_manager.send_to_rhino(session_id, "delete_rhino_objects", params)
            return handle_tool_exe_response("deleting objects", session_id, result)
        except Exception as e:
            return handle_error("deleting objects", session_id, e)

    @mcp.tool()
    async def modify_rhino_objects(session_id: str, objects: List[Dict[str, Any]], all: bool = False) -> str:
        """Apply geometric transformations to objects in Rhino document.
        
        This function applies transformations like move, rotate, scale to objects.
        Each object modification should specify the target object and transformation.
        
        Available transformations:
        - move: Translate object by vector
        - rotate: Rotate object around axis  
        - scale: Scale object by factor(s)
        - mirror: Mirror object across plane
        
        Args:
            session_id: The session ID of the connected Rhino instance
            objects: List of modification operations, each containing:
                - target: Object identifier (id or name)
                - operation: Transformation type ("move", "rotate", "scale", "mirror")
                - params: Operation-specific parameters
            all: If true, applies transformations to all objects in document
        
        Returns:
            JSON string containing modification results
        """
        try:
            params = {
                "objects": objects
            }
            if all:
                params["all"] = True
                  
            result = await connection_manager.send_to_rhino(session_id, "modify_rhino_objects", params)
            return handle_tool_exe_response("modifying objects", session_id, result)
        except Exception as e:
            return handle_error("modifying objects", session_id, e)
