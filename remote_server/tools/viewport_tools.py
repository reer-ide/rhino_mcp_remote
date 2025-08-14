"""Viewport capture tools for Rhino."""
import base64
import io
from fastmcp import Context
from mcp.types import ImageContent
from typing import Optional
from remote_server.connection_manager import ConnectionManager
from remote_server.utils.tool_helpers import handle_error


def register_tools(mcp, connection_manager: Optional[ConnectionManager]):
    """Register viewport tools with the MCP server."""
    
    @mcp.tool()
    async def capture_rhino_viewport(session_id: str, layer: Optional[str] = None, show_annotations: bool = False, max_size: int = 800) -> ImageContent:
        """Capture the current viewport as an image.
        
        Args:
            session_id: The session ID of the connected Rhino instance
            layer: Optional layer name to show exclusively in capture
            show_annotations: Whether to include annotations in the capture, condiser turning this on only when several objects are in the viewport
            max_size: Maximum size for the captured image in pixels
            
        Returns:
            Image object containing the captured viewport
        """
        try:
            params = {
                "layer": layer,
                "show_annotations": show_annotations,
                "max_size": max_size
            }
            # Get connection manager lazily
            from remote_server.dependencies import get_connection_manager
            conn_mgr = await get_connection_manager()
            
            result = await conn_mgr.send_to_rhino(session_id, "capture_rhino_viewport", params)
            
            # The C# client wraps responses in a structure like:
            # { "type": "response", "correlation_id": "...", "status": "success", "result": { actual_tool_result } }
            # We need to extract the actual result
            actual_result = result
            if result.get("type") == "response" and "result" in result:
                actual_result = result["result"]
            
            if actual_result.get("type") == "image":
                # Extract base64 data from the C# response structure
                source = actual_result.get("source", {})
                if source["type"] == "base64":
                    base64_data = source["data"]
                    media_type = source["media_type"]
                    
                    if base64_data:                        
                        # Create FastMCP Image object
                        return ImageContent(type="image",
                                            data=base64_data,
                                            mimeType=media_type,
                                            annotations=None)
                    else:
                        raise Exception("No image data found in response")
                else:
                    raise Exception(f"Expected base64 source type, got: {source.get('type')}")
            else:
                raise Exception(f"Unexpected response type: {actual_result.get('type')}")
                  
        except Exception as e:
            return handle_error("capturing viewport", session_id, e)

