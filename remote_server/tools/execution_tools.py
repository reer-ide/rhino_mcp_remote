"""Code execution tools for Rhino."""
from fastmcp import Context
from ._base import BaseTool
from remote_server.connection_manager import ConnectionManager


class ExecutionTools(BaseTool):
    """Tools for executing code in Rhino."""
    
    async def execute_rhino_code(self, ctx: Context, session_id: str, code: str) -> str:
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
            result = await self.send_to_rhino(session_id, "execute_rhino_script", {"code": code})
            
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
            return self.handle_error("executing code", session_id, e)


def register_tools(app, connection_manager: ConnectionManager):
    """Register execution tools with the MCP server."""
    tools = ExecutionTools(connection_manager)
    app.tool()(tools.execute_rhino_code) 