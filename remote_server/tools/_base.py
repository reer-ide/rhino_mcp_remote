"""Base class for Rhino MCP tools."""
import json
import logging
from typing import Any, Dict, Optional
from fastmcp import Context
from remote_server.connection_manager import ConnectionManager

logger = logging.getLogger("RhinoTools")


class BaseTool:
    """Base class for all Rhino MCP tools."""
    
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager
    
    async def send_to_rhino(self, session_id: str, command: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send a command to Rhino and return the result.
        
        Args:
            session_id: The session ID of the connected Rhino instance
            command: The command to send to Rhino
            params: Optional parameters for the command
            
        Returns:
            The result from Rhino
            
        Raises:
            Exception: If there's an error communicating with Rhino
        """
        try:
            return await self.connection_manager.send_to_rhino(session_id, command, params)
        except Exception as e:
            logger.error(f"Error sending command '{command}' to Rhino session {session_id}: {str(e)}")
            raise
    
    def format_json_response(self, result: Dict[str, Any]) -> str:
        """Format a result dictionary as a JSON string.
        
        Args:
            result: The result dictionary to format
            
        Returns:
            JSON formatted string
        """
        return json.dumps(result, indent=2)
    
    def handle_error(self, operation: str, session_id: str, error: Exception) -> str:
        """Handle and log errors consistently.
        
        Args:
            operation: Description of the operation that failed
            session_id: The session ID where the error occurred
            error: The exception that occurred
            
        Returns:
            Formatted error message
        """
        error_msg = f"Error {operation} in session {session_id}: {str(error)}"
        logger.error(error_msg)
        return error_msg 