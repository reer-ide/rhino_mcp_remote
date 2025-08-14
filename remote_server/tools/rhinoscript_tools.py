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
        1. This is Rhino 7 with IronPython 2.7 - no f-strings or modern Python features
        2. Use add_rhino_objects_metadata(object_ids, name, description) after creating objects to add metadata
        3. Use rhinoscriptsyntax functions for object creation and manipulation
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
            Execution result
        """
        try:
            # Get connection manager lazily
            from remote_server.dependencies import get_connection_manager
            conn_mgr = await get_connection_manager()
            
            result = await conn_mgr.send_to_rhino(session_id, "execute_rhino_script", {"code": code})
            return handle_tool_exe_response("executing code", session_id, result)
                
        except Exception as e:
            return handle_error("executing code", session_id, e)


