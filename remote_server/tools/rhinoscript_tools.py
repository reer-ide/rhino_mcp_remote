"""Code execution tools for Rhino."""
import json
from fastmcp import Context
from typing import Optional, Dict, Any
try:
    from ..connection_manager import ConnectionManager
except ImportError:
    from remote_server.connection_manager import ConnectionManager
from remote_server.utils.tool_helpers import handle_tool_exe_response, handle_error


def register_tools(mcp, connection_manager: Optional[ConnectionManager]):
    """Register execution tools with the MCP server."""
    
    @mcp.tool()
    async def execute_rhinoscript(session_id: str, code: str) -> str:
        """Execute arbitrary Python code in Rhino.
        
        IMPORTANT NOTES FOR CODE EXECUTION:
        1. This code runs in the Rhino and uses IronPython 2.7, so the syntax and libraries are limited:
              - No Python 3 features (f-strings, type hints, async/await, etc.,)
              - No external libraries (only built-in and Rhino libraries)
        2. Already imported for you, so do NOT import again and use directly:
            import rhinoscriptsyntax as rs
            import scriptcontext as sc
            import json
            import Rhino
            import clr
        3. All the other tools are available to use directly in your code as well following the same pattern and return types unless otherwise noted:
            - get_rhino_scene_info()
            - get_rhino_selected_objects() (NOTE: this will return list of Rhino ObjRef objects so you can use obj_ref.Face() etc. to access subobject directly)
            - get_rhino_objects_info(object_ids=None)
            - create_rhino_basic_geometries(objects)
            - create_rhino_layers(layers)
            - delete_rhino_objects(object_ids=None, all=False)
            - delete_rhino_layers(layer_names)
            - add_rhino_objects_metadata(object_ids, name=None, description=None)
            - update_rhino_objects_metadata(object_ids, name=None, description=None)
            - select_filtered_rhino_objects(filters=None, **kwargs)
            - modify_rhino_objects(object_ids, operations)
            - capture_rhino_viewport(width=800, height=600, view_name=None)
        2. Use add_rhino_objects_metadata(object_ids, name, description) after creating objects to add metadata
    
        4. For basic geometries, consider using create_rhino_basic_geometries tool instead for simpler usage

        Common Syntax Errors to Avoid:
        - No walrus operator (:=)
        - No type hints
        - No modern Python features (match/case, etc.)
        - No list/dict comprehensions with multiple for clauses
        - No assignment expressions in if/while conditions
        - No f-strings! Use .format() or % formatting instead

        Example of object creation with metadata:
        ```python
        # Create geometry
        cube_id = rs.AddBox(corners)
        # Add metadata
        add_rhino_objects_metadata([cube_id], "Building Block", "Main structural element")
        ```
        
        Args:
            session_id: The session ID of the connected Rhino instance
            code: Python code to execute in Rhino
            
        Returns:
            JSON string with structure:
            {
              "status": "success",
              "message": "Code executed successfully",
              "printed_output": "Any print output from the code",
              "new_objects_count": 5,
              "new_objects": ["guid-1", "guid-2", "guid-3", "guid-4", "guid-5"]
            }
            
            On error:
            {
              "status": "error",
              "error": "Error message"
            }
        """
        try:
            # Get connection manager lazily
            from remote_server.dependencies import get_connection_manager
            conn_mgr = await get_connection_manager()
            
            result = await conn_mgr.send_to_rhino(session_id, "execute_rhino_script", {"code": code})
            return handle_tool_exe_response("executing code", session_id, result)
                
        except Exception as e:
            return handle_error("executing code", session_id, e)


