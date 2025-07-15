"""Object creation, modification, and deletion tools for Rhino."""
from fastmcp import Context
from typing import List, Dict, Any, Optional
from ._base import BaseTool
from remote_server.connection_manager import ConnectionManager


class ObjectTools(BaseTool):
    """Tools for managing Rhino objects."""
    
    async def create_rhino_basic_objects(self, ctx: Context, session_id: str, objects: List[Dict[str, Any]]) -> str:
        """Create multiple basic geometry objects in Rhino at once
        
        This tool allows you to create multiple basic geometry objects of different types in Rhino at once. 
        Every created object MUST have a name for easier identification and management.
        
        Supported geometry object types and their parameters:
        
        - POINT: Create a 3D point
          Parameters: x, y, z (coordinates)
        
        - LINE: Create a line between two points
          Parameters: start [x,y,z], end [x,y,z]
        
        - POLYLINE: Create a polyline through multiple points
          Parameters: points [[x,y,z], [x,y,z], ...]
        
        - CIRCLE: Create a circle
          Parameters: center [x,y,z], radius
        
        - ARC: Create an arc
          Parameters: center [x,y,z], radius, angle (in degrees)
        
        - ELLIPSE: Create an ellipse
          Parameters: center [x,y,z], radius_x, radius_y
        
        - CURVE: Create a NURBS curve
          Parameters: points [[x,y,z], [x,y,z], ...], degree (optional, default 3)
        
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
                - description: Optional description text
                - color: Optional RGB color array [r, g, b] (0-255)
                - layer: Optional layer name
                - translation: Optional [x, y, z] translation vector
                - rotation: Optional [x, y, z] rotation in radians
                - scale: Optional [x, y, z] scale factors
        
        Examples:
            # Create multiple objects at once
            create_rhino_basic_geometries("session123", [
                {
                    "type": "box",
                    "name": "MyBox",
                    "params": {
                        "center": [0, 0, 0],
                        "width": 2.0,
                        "length": 1.0,
                        "height": 1.5
                    },
                    "description": "A sample box",
                    "color": [255, 0, 0],
                    "translation": [0, 0, 0]
                },
                {
                    "type": "sphere",
                    "name": "MySphere",
                    "params": {
                        "center": [3, 0, 0],
                        "radius": 1.0
                    },
                    "description": "A sample sphere",
                    "color": [0, 255, 0],
                    "scale": [1.5, 1.5, 1.5]
                }
            ])
            
        Returns:
            JSON string containing the created geometries with their metadata
        """
        try:
            # Validate that all objects have required fields
            for i, obj in enumerate(objects):
                if "type" not in obj:
                    return f"Error: Object {i} missing 'type' field"
                if "name" not in obj:
                    return f"Error: Object {i} missing 'name' field"
                if "params" not in obj:
                    return f"Error: Object {i} missing 'params' field"
            
            params = {
                "objects": objects
            }
            result = await self.send_to_rhino(session_id, "create_rhino_basic_geometries", params)
            return self.format_json_response(result)
        except Exception as e:
            return self.handle_error("creating basic geometries", session_id, e)

    async def delete_rhino_objects(self, ctx: Context, session_id: str, objects: List[Dict[str, Any]] = None, id: str = None, name: str = None, all: bool = False) -> str:
        """Delete objects from Rhino document.
        
        Args:
            session_id: The session ID of the connected Rhino instance
            objects: List of object identifiers (new format)
            id: Object GUID to delete (single object format for backward compatibility)
            name: Object name to delete (single object format for backward compatibility)
            all: Delete all objects in the document
            
        Object deletion format:
            {
                "id": "object-guid",      # Either id or name required
                "name": "object_name",    # Either id or name required
                "quiet": true             # Optional - suppress warnings during deletion
            }
            
        Note:
            - Locked objects cannot be deleted
            - Use all=true to delete all objects in document
            
        Examples:
            # Multiple objects
            objects = [
                {"id": "object-guid-1"},
                {"name": "MyBox"},
                {"id": "object-guid-2", "quiet": false}
            ]
            
            # Single object (backward compatibility)
            id = "object-guid-here"
            name = "ObjectName"
            
            # Delete all objects
            all = true
            
        Returns:
            JSON string containing deletion results and status
        """
        try:
            params = {}
            
            if all:
                params["all"] = True
            elif objects is not None:
                params["objects"] = objects
            else:
                # Single object format for backward compatibility
                if id is not None:
                    params["id"] = id
                if name is not None:
                    params["name"] = name
                    
            result = await self.send_to_rhino(session_id, "delete_rhino_objects", params)
            return self.format_json_response(result)
        except Exception as e:
            return self.handle_error("deleting objects", session_id, e)

    async def modify_rhino_objects(self, ctx: Context, session_id: str, objects: List[Dict[str, Any]], all: bool = False) -> str:
        """Apply geometric transformations to objects in Rhino document.
        
        Args:
            session_id: The session ID of the connected Rhino instance
            objects: List of object transformations with id/name and transformation parameters
            all: Apply the first transformation set to all objects in the document
            
        Object transformation format:
            {
                "id": "object-guid",              # Either id or name required to identify object
                "name": "object_name",            # Either id or name required to identify object
                "translation": [x, y, z],         # Optional - move object by vector
                "rotation": [rx, ry, rz],         # Optional - rotate around X, Y, Z axes (radians)
                "scale": [sx, sy, sz],            # Optional - scale factors for X, Y, Z axes
                "scale": 2.0,                     # Alternative - uniform scale factor
                "new_name": "updated_name",       # Optional - rename object
                "new_color": [255, 0, 0]          # Optional - change object color RGB
            }
            
        Transformation details:
            - translation: Moves object by [x, y, z] vector in world units
            - rotation: Rotates around object center, angles in radians [Rx, Ry, Rz]
            - scale: Scales from object center, can be [x, y, z] or single uniform value
            - All transformations use object's bounding box center as reference point
            - Locked objects cannot be modified
            
        Note:
            - Use all=true with single transformation to apply to all objects
            - Transformations are applied in order: translation → scale → rotation
            - Object identification by either GUID or name
            
        Examples:
            # Move and rotate specific objects
            objects = [
                {
                    "id": "object-guid-1",
                    "translation": [10, 0, 0],     # Move 10 units in X direction
                    "rotation": [0, 0, 1.57]       # Rotate 90 degrees around Z axis
                },
                {
                    "name": "MyBox",
                    "scale": [2, 1, 1],            # Scale 2x in X direction only
                    "new_color": [255, 0, 0]       # Make it red
                }
            ]
            
            # Scale all objects uniformly
            objects = [{"scale": 1.5}]            # 150% scale
            all = true
            
        Returns:
            JSON string containing transformation results and object information
        """
        try:
            params = {
                "objects": objects
            }
            
            if all:
                params["all"] = True
                    
            result = await self.send_to_rhino(session_id, "modify_rhino_objects", params)
            return self.format_json_response(result)
        except Exception as e:
            return self.handle_error("modifying objects", session_id, e)


def register_tools(app, connection_manager: ConnectionManager):
    """Register object tools with the MCP server."""
    tools = ObjectTools(connection_manager)
    app.tool()(tools.create_rhino_basic_objects)
    app.tool()(tools.delete_rhino_objects)
    app.tool()(tools.modify_rhino_objects) 