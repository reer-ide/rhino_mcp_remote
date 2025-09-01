"""Object creation, modification, and deletion tools for Rhino."""
from fastmcp import Context
from typing import List, Dict, Any, Optional
from remote_server.connection_manager import ConnectionManager
from remote_server.utils.tool_helpers import handle_tool_exe_response, handle_error


def register_tools(mcp, connection_manager: Optional[ConnectionManager]):
    """Register object tools with the MCP server."""
    
    @mcp.tool()
    async def create_rhino_basic_geometries(session_id: str, objects: List[Dict[str, Any]]) -> str:
        """Create multiple basic geometry objects in Rhino at once
        
        This function efficiently creates multiple geometric objects in a single operation.
        Each object must specify its type and required parameters.
        
        Supported object types and their parameters:
        
        - POINT: Create a point
          Parameters: x, y, z (coordinates)
          Sample: {"type": "point", "name": "Point1", "params": {"x": 0, "y": 0, "z": 0}}
        
        - LINE: Create a line segment  
          Parameters: start [x,y,z], end [x,y,z]
          Sample: {"type": "line", "name": "Line1", "params": {"start": [0,0,0], "end": [1,1,1]}}
        
        - POLYLINE: Create a polyline through points
          Parameters: points [[x,y,z], [x,y,z], ...]
          Sample: {"type": "polyline", "name": "Polyline1", "params": {"points": [[0,0,0], [1,1,1], [2,0,0]]}}

        - CURVE: Create a curve through control points
          Parameters: points [[x,y,z], [x,y,z], ...], degree (optional, default 3)
          Sample: {"type": "curve", "name": "Curve1", "params": {"points": [[0,0,0], [1,1,1], [2,0,0]], "degree": 3}}
        
        - CIRCLE: Create a circle
          Parameters: center [x,y,z], radius
          Sample: {"type": "circle", "name": "Circle1", "params": {"center": [0,0,0], "radius": 5.0}}
        
        - ARC: Create an arc
          Parameters: center [x,y,z], radius, angle (degrees - total arc angle)
          Sample: {"type": "arc", "name": "Arc1", "params": {"center": [0,0,0], "radius": 5.0, "angle": 90}}
        
        - ELLIPSE: Create an ellipse
          Parameters: center [x,y,z], radius_x, radius_y
          Sample: {"type": "ellipse", "name": "Ellipse1", "params": {"center": [0,0,0], "radius_x": 5.0, "radius_y": 3.0}}
        
        - RECTANGLE: Create a rectangle 
          Parameters: center [x,y,z], width, height
          Sample: {"type": "rectangle", "name": "Rectangle1", "params": {"center": [0,0,0], "width": 10.0, "height": 5.0}}
        
        - POLYGON: Create a regular polygon
          Parameters: center [x,y,z], radius, sides
          Sample: {"type": "polygon", "name": "Polygon1", "params": {"center": [0,0,0], "radius": 5.0, "sides": 6}}
        
        - BOX: Create a box/cuboid
          Parameters: center [x,y,z], width, length, height
          Sample: {"type": "box", "name": "Box1", "params": {"center": [0,0,0], "width": 5.0, "length": 10.0, "height": 3.0}}
        
        - SPHERE: Create a sphere
          Parameters: center [x,y,z], radius
          Sample: {"type": "sphere", "name": "Sphere1", "params": {"center": [0,0,0], "radius": 5.0}}
        
        - CONE: Create a cone
          Parameters: center [x,y,z], radius, height, cap (optional, default true)
          Sample: {"type": "cone", "name": "Cone1", "params": {"center": [0,0,0], "radius": 3.0, "height": 10.0}}
        
        - CYLINDER: Create a cylinder
          Parameters: center [x,y,z], radius, height, cap (optional, default true)
          Sample: {"type": "cylinder", "name": "Cylinder1", "params": {"center": [0,0,0], "radius": 3.0, "height": 10.0}}
        
        - TORUS: Create a torus
          Parameters: center [x,y,z], major_radius, minor_radius
          Sample: {"type": "torus", "name": "Torus1", "params": {"center": [0,0,0], "major_radius": 5.0, "minor_radius": 2.0}}
        
        - PLANE: Create a plane surface
          Parameters: center [x,y,z], width, height
          Sample: {"type": "plane", "name": "Plane1", "params": {"center": [0,0,0], "width": 10.0, "height": 5.0}}
        
        Args:
            session_id: The session ID of the connected Rhino instance
            objects: List of objects to create, each containing:
                - type: REQUIRED geometry type (e.g., "point", "line", "box", "sphere")
                - name: REQUIRED name for the object (for easier identification)
                - params: REQUIRED dictionary of geometry-specific parameters
                - description: OPTIONAL description for the object
                - color: OPTIONAL color as hex string (e.g., "#FF0000") or RGB array
                - layer: OPTIONAL layer name for the object
        
        Returns:
            JSON string with structure:
            {
              "status": "success",  // or "partial_success" if some objects failed
              "count": 3,
              "created": 3,
              "errors": 0,
              "objects": [
                {
                  "object_id": "guid-string",
                  "name": "Point1",
                  "type": "POINT",
                  "description": "Point description",
                  "metadata_applied": true
                }
              ]
            }
            
            On error:
            {
              "error": "Error creating geometries: error message"
            }
        """
        try:
            # Get connection manager lazily
            from remote_server.dependencies import get_connection_manager
            conn_mgr = await get_connection_manager()
            
            params = {
                "objects": objects
            }
            result = await conn_mgr.send_to_rhino(session_id, "create_rhino_basic_geometries", params)
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
                  
            # Get connection manager lazily
            from remote_server.dependencies import get_connection_manager
            conn_mgr = await get_connection_manager()
            
            result = await conn_mgr.send_to_rhino(session_id, "delete_rhino_objects", params)
            return handle_tool_exe_response("deleting objects", session_id, result)
        except Exception as e:
            return handle_error("deleting objects", session_id, e)

    @mcp.tool()
    async def modify_rhino_objects(session_id: str, targets: List[Dict[str, Any]], operations: List[Dict[str, Any]], execution: str = "combined") -> str:
        """Apply geometric transformations and attribute changes to objects in Rhino document.
        
        This function supports chained operations with flexible targeting and execution modes.
        Operations can be applied as a single combined transformation or sequentially.
        
        Available operation types:
        - translate: Move object by vector [x, y, z]
        - rotate: Rotate object by angle (degrees) around axis [x, y, z] 
        - scale: Scale object by factor with optional center point
        - rename: Change object name
        - recolor: Change object color [r, g, b]
        
        Args:
            session_id: The session ID of the connected Rhino instance
            targets: List of target objects, each containing one of:
                - {"id": "object-guid"} - Target specific object by ID
                - {"name": "object-name"} - Target object by name  
                - {"all": true} - Target all objects in document
            operations: List of operations to apply, each containing:
                - {"type": "translate", "vector": [x, y, z]}
                - {"type": "rotate", "angle": degrees, "axis": [x, y, z], "center": "auto|origin|[x,y,z]"}
                - {"type": "scale", "factor": number, "center": "auto|origin|[x,y,z]"}
                - {"type": "rename", "name": "new-name"}
                - {"type": "recolor", "color": [r, g, b]}
            execution: Execution mode - "combined" (default) or "sequential"
                - "combined": All transforms applied as single matrix
                - "sequential": Operations applied one by one in order
        
        Returns:
            JSON string containing detailed modification results for each object
        """
        try:
            params = {
                "targets": targets,
                "operations": operations,
                "execution": execution
            }
                  
            # Get connection manager lazily
            from remote_server.dependencies import get_connection_manager
            conn_mgr = await get_connection_manager()
            
            result = await conn_mgr.send_to_rhino(session_id, "modify_rhino_objects", params)
            return handle_tool_exe_response("modifying objects", session_id, result)
        except Exception as e:
            return handle_error("modifying objects", session_id, e)
