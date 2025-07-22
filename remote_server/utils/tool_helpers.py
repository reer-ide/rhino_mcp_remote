"""Shared utility functions for MCP tool response and error handling."""
import json
import logging
from typing import Dict, Any, Union

logger = logging.getLogger("RhinoTools")

def handle_error(operation: str, session_id: str, error: Exception) -> str:
    """Handle and log errors consistently across all tools.
    
    Args:
        operation: Description of the operation that failed
        session_id: The session ID where the error occurred
        error: The exception that was raised
        
    Returns:
        Error message string that can be returned to the client
    """
    error_msg = f"Error {operation} in session {session_id}: {str(error)}"
    logger.error(error_msg)
    return error_msg


def handle_tool_exe_response(operation: str, session_id: str, response_data: Union[str, Dict[str, Any]]) -> str:
    """Handle response from Rhino, checking for errors and formatting appropriately.
    
    Args:
        operation: Description of the operation that was performed
        session_id: The session ID where the operation occurred
        response_data: Raw response from the Rhino (JSON string or dict)
        
    Returns:
        Formatted response string
        
    Raises:
        Exception: If the Rhino response indicates an error
    """
    try:
        # Parse the response if it's a string
        if isinstance(response_data, str):
            try:
                result = json.loads(response_data)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Rhino response for {operation} in session {session_id}: {e}")
                raise Exception(f"Invalid JSON response from Rhino: {str(e)}")
        else:
            result = response_data
        
        # Remove correlation_id wrapper if present (for responses from WebSocket client)
        result = unwrap_correlation_response(result)
        
        # Check if the response indicates an error
        if is_error_response(result):
            error_message = extract_error_message(result)
            logger.error(f"Plugin error during {operation} in session {session_id}: {error_message}")
            raise Exception(f"Plugin error: {error_message}")
        
        # Log successful operation
        logger.info(f"Successfully completed {operation} in session {session_id}")
        
        # Return formatted response
        return json.dumps(result, indent=2)
        
    except Exception as e:
        # If it's already our exception, re-raise it
        if "Plugin error:" in str(e) or "Invalid JSON response" in str(e):
            raise
        # Otherwise, wrap it as a general error
        error_msg = f"Error processing Rhino response for {operation} in session {session_id}: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)


def unwrap_correlation_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """Remove correlation_id wrapper from response if present.
    
    The WebSocket client may wrap responses in a structure like:
    { "type": "response", "correlation_id": "...", "result": { actual_tool_result } }
    
    This function unwraps such responses to return the actual tool result.
    
    Args:
        response: The response dictionary (potentially wrapped)
        
    Returns:
        The unwrapped response dictionary
    """
    if (response.get("type") == "response" and 
        "result" in response and 
        "correlation_id" in response):
        return response["result"]
    return response


def is_error_response(response: Dict[str, Any]) -> bool:
    """Check if a response from the plugin indicates an error.
    
    Args:
        response: The parsed response dictionary from the Rhino
        
    Returns:
        True if the response indicates an error, False otherwise
    """
    # Check for explicit error field
    if response.get("error") is not None:
        return True
    
    # Check for status field indicating error
    status = response.get("status", "").lower()
    if status == "error":
        return True
    
    return False


def extract_error_message(response: Dict[str, Any]) -> str:
    """Extract error message from a Rhino error response.
    
    Args:
        response: The parsed error response dictionary from the Rhino
        
    Returns:
        The error message string
    """
    # Try to get error message from 'error' field
    if response.get("error"):
        return str(response["error"])
    
    # Try to get error message from 'message' field
    if response.get("message"):
        return str(response["message"])
    
    # Fallback to generic message
    return "Unknown error occurred"


def format_success_response(operation: str, session_id: str, result: Dict[str, Any]) -> str:
    """Format a successful operation response.
    
    Args:
        operation: Description of the successful operation
        session_id: The session ID where the operation occurred
        result: The result data from the operation
        
    Returns:
        Formatted JSON response string
    """
    logger.info(f"Successfully completed {operation} in session {session_id}")
    return json.dumps(result, indent=2)


def validate_session_id(session_id: str) -> bool:
    """Validate that a session ID is provided and not empty.
    
    Args:
        session_id: The session ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    return session_id and session_id.strip()