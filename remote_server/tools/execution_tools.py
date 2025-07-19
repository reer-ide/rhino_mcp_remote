"""Code execution tools for Rhino."""
import json
import logging
from fastmcp import Context
from typing import Optional, Dict, Any
try:
    from ..connection_manager import ConnectionManager
except ImportError:
    from remote_server.connection_manager import ConnectionManager

logger = logging.getLogger("RhinoTools")


def _handle_error(operation: str, session_id: str, error: Exception) -> str:
    """Handle and log errors consistently."""
    error_msg = f"Error {operation} in session {session_id}: {str(error)}"
    logger.error(error_msg)
    return error_msg


def register_tools(mcp, connection_manager: ConnectionManager):
    """Register execution tools with the MCP server."""
    
    @mcp.tool()
    async def execute_rhino_code(session_id: str, code: str) -> str:
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
            result = await connection_manager.send_to_rhino(session_id, "execute_rhino_script", {"code": code})
            
            # Handle the response
            if result.get("status") == "error":
                error_msg = f"Error: {result.get('error', 'Unknown error')}"
                return error_msg
            else:
                response_parts = []
                response_parts.append(result.get("message", "Code executed successfully"))
                
                # Add printed output if available
                printed_output = result.get("printed_output", [])
                if printed_output:
                    response_parts.append("\nPrinted output:")
                    response_parts.extend(printed_output)
                
                return "\n".join(response_parts)
                
        except Exception as e:
            return _handle_error("executing code", session_id, e)


