"""Utility tools for basic server operations."""
from fastmcp import Context
from ._base import BaseTool
from remote_server.connection_manager import ConnectionManager


class UtilityTools(BaseTool):
    """Basic utility tools for server operations."""
    
    async def ping(self, ctx: Context, session_id: str) -> str:
        """Ping the Rhino session to check if it is connected.
        
        Args:
            session_id: The session ID of the connected Rhino instance
            
        Returns:
            JSON string containing the ping response
        """
        try:
            result = await self.send_to_rhino(session_id, "ping")
            return self.format_json_response(result)
        except Exception as e:
            return self.handle_error("pinging Rhino", session_id, e)


def register_tools(app, connection_manager: ConnectionManager):
    """Register utility tools with the MCP server."""
    tools = UtilityTools(connection_manager)
    app.tool()(tools.ping) 