"""Viewport capture tools for Rhino."""
import base64
import io
from PIL import Image as PILImage
from fastmcp import Context
from fastmcp.utilities.types import Image
from typing import Optional
from ._base import BaseTool
from remote_server.connection_manager import ConnectionManager


class ViewportTools(BaseTool):
    """Tools for viewport operations."""
    
    async def capture_rhino_viewport(self, ctx: Context, session_id: str, layer: Optional[str] = None, show_annotations: bool = True, max_size: int = 800) -> Image:
        """Capture the current viewport as an image.
        
        Args:
            session_id: The session ID of the connected Rhino instance
            layer: Optional layer name to filter annotations
            show_annotations: Whether to show object annotations
            max_size: Maximum size for the captured image
        
        Returns:
            An MCP Image object containing the viewport capture
        """
        try:
            params = {
                "layer": layer,
                "show_annotations": show_annotations,
                "max_size": max_size
            }
            result = await self.send_to_rhino(session_id, "capture_rhino_viewport", params)
            
            if result.get("type") == "image":
                # Get base64 data from Rhino
                base64_data = result["source"]["data"]
                
                # Convert base64 to bytes
                image_bytes = base64.b64decode(base64_data)
                
                # Create PIL Image from bytes
                img = PILImage.open(io.BytesIO(image_bytes))
                
                # Convert to PNG format for better quality and consistency
                png_buffer = io.BytesIO()
                img.save(png_buffer, format="PNG")
                png_bytes = png_buffer.getvalue()
                
                # Return as MCP Image object
                return Image(data=png_bytes, format="png")
                
            else:
                raise Exception(result.get("text", "Failed to capture viewport"))
                
        except Exception as e:
            self.handle_error("capturing viewport", session_id, e)
            raise


def register_tools(app, connection_manager: ConnectionManager):
    """Register viewport tools with the MCP server."""
    tools = ViewportTools(connection_manager)
    app.tool()(tools.capture_rhino_viewport) 