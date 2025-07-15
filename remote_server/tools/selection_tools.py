"""Object selection tools for Rhino."""
from fastmcp import Context
from typing import Dict, Any
from ._base import BaseTool
from remote_server.connection_manager import ConnectionManager


class SelectionTools(BaseTool):
    """Tools for managing object selection."""
    
    async def get_rhino_selected_objects(self, ctx: Context, session_id: str, include_lights: bool = False, include_grips: bool = False) -> str:
        """Get the identifiers of all objects that are currently selected in Rhino.
        
        This tool provides access to objects that have been manually selected in the Rhino viewport.
        It returns a list of object identifiers (GUIDs) that can be used with other Rhino functions.
        
        Args:
            session_id: The session ID of the connected Rhino instance
            include_lights: Whether to include light objects in the selection
            include_grips: Whether to include grip objects in the selection
        
        Returns:
            JSON string containing the selected object identifiers and metadata
        """
        try:
            params = {
                "include_lights": include_lights,
                "include_grips": include_grips
            }
            result = await self.send_to_rhino(session_id, "get_rhino_selected_objects", params)
            return self.format_json_response(result)
        except Exception as e:
            return self.handle_error("getting selected objects", session_id, e)

    async def select_rhino_objects(self, ctx: Context, session_id: str, filters: Dict[str, Any] = {}, filters_type: str = "and") -> str:
        """Select Rhino objects based on filters.
        
        Args:
            session_id: The session ID of the connected Rhino instance
            filters: Dictionary containing filters such as:
                - name: List of object names to match
                - color: List of RGB color arrays [R, G, B] to match
                - layer: List of layer names to match
                - custom_attribute: List of values for any custom user string attribute
            filters_type: Filter logic - "and" (all filters must match) or "or" (any filter matches)
            
        Note:
            - Filter values are always lists, even for single values
            - If filters is empty, all objects will be selected
            - Custom attributes are matched by their user string key names
            
        Examples:
            filters = {"name": ["box1", "box2"], "category": ["furniture"]}
            filters = {"color": [[255, 0, 0], [0, 255, 0]]}  # Red or green objects
            filters = {"layer": ["Architecture", "Structure"]}  # Objects on specific layers
            
        Returns:
            JSON string containing the count of selected objects and their IDs
        """
        try:
            params = {
                "filters": filters,
                "filters_type": filters_type
            }
            result = await self.send_to_rhino(session_id, "select_rhino_objects", params)
            return self.format_json_response(result)
        except Exception as e:
            return self.handle_error("selecting objects", session_id, e)


def register_tools(app, connection_manager: ConnectionManager):
    """Register selection tools with the MCP server."""
    tools = SelectionTools(connection_manager)
    app.tool()(tools.get_rhino_selected_objects)
    app.tool()(tools.select_rhino_objects) 