"""Tools for interacting with Rhino through WebSocket connection."""
from fastmcp import Context, Image
import logging
from typing import Dict, Any, List, Optional
import json
import base64
import io
from PIL import Image as PILImage
import requests
import re
from remote_server.utils.rhino_script_categories import get_function_category
from remote_server.connection_manager import ConnectionManager

# Configure logging
logger = logging.getLogger("RhinoTools")

class RhinoTools:
    """Collection of tools for interacting with Rhino via WebSocket."""
    
    def __init__(self, app, connection_manager: ConnectionManager):
        self.app = app
        self.connection_manager = connection_manager
        self._register_tools()
    
    def _register_tools(self):
        """Register all Rhino tools with the MCP server."""
        self.app.tool()(self.get_rhino_scene_info)
        self.app.tool()(self.get_rhino_layers)
        self.app.tool()(self.get_rhino_objects_with_metadata)
        self.app.tool()(self.capture_rhino_viewport)
        self.app.tool()(self.execute_rhino_code)
        self.app.tool()(self.get_rhino_selected_objects)
        self.app.tool()(self.look_up_RhinoScriptSyntax)
    
    async def get_rhino_scene_info(self, ctx: Context, session_id: str) -> str:
        """Get basic information about the current Rhino scene.
        
        This is a lightweight function that returns basic scene information:
        - List of all layers with basic information about the layer and 5 sample objects with their metadata 
        - No metadata or detailed properties
        - Use this for quick scene overview or when you only need basic object information
        
        Args:
            session_id: The session ID of the connected Rhino instance
            
        Returns:
            JSON string containing basic scene information
        """
        try:
            result = await self.connection_manager.send_to_rhino(session_id, "get_rhino_scene_info")
            return json.dumps(result, indent=2)
        except Exception as e:
            logger.error(f"Error getting scene info from Rhino session {session_id}: {str(e)}")
            return f"Error getting scene info: {str(e)}"

    async def get_rhino_layers(self, ctx: Context, session_id: str) -> str:
        """Get list of layers in Rhino
        
        Args:
            session_id: The session ID of the connected Rhino instance
            
        Returns:
            JSON string containing layer information
        """
        try:
            result = await self.connection_manager.send_to_rhino(session_id, "get_rhino_layers")
            return json.dumps(result, indent=2)
        except Exception as e:
            logger.error(f"Error getting layers from Rhino session {session_id}: {str(e)}")
            return f"Error getting layers: {str(e)}"

    async def get_rhino_objects_with_metadata(self, ctx: Context, session_id: str, filters: Optional[Dict[str, Any]] = None, metadata_fields: Optional[List[str]] = None) -> str:
        """Get detailed information about objects in the scene with their metadata.
        
        This is a CORE FUNCTION for scene context awareness. It provides:
        1. Full metadata for each object we created via this mcp connection including:
           - short_id (DDHHMMSS format), can be displayed in the viewport when using capture_rhino_viewport, can help visually identify the object and find it with this function
           - created_at timestamp
           - layer  - layer path
           - type - geometry type 
           - bbox - the bounding box as list of points
           - name - the name you assigned 
           - description - description you assigned 
        
        2. Advanced filtering capabilities:
           - layer: Filter by layer name (supports wildcards, e.g., "Layer*")
           - name: Filter by object name (supports wildcards, e.g., "Cube*")
           - short_id: Filter by exact short ID match
        
        3. Field selection:
           - Can specify which metadata fields to return
           - Useful for reducing response size when only certain fields are needed
        
        Args:
            session_id: The session ID of the connected Rhino instance
            filters: Optional dictionary of filters to apply
            metadata_fields: Optional list of specific metadata fields to return
        
        Returns:
            JSON string containing filtered objects with their metadata
        """
        try:
            params = {
                "filters": filters or {},
                "metadata_fields": metadata_fields
            }
            result = await self.connection_manager.send_to_rhino(session_id, "get_rhino_objects_with_metadata", params)
            return json.dumps(result, indent=2)
        except Exception as e:
            logger.error(f"Error getting objects with metadata from session {session_id}: {str(e)}")
            return f"Error getting objects with metadata: {str(e)}"

    async def capture_rhino_viewport(self, ctx: Context, session_id: str, layer: Optional[str] = None, show_annotations: bool = True, max_size: int = 800) -> Image:
        """Capture the current viewport as an image.
        
        Args:
            session_id: The session ID of the connected Rhino instance
            layer: Optional layer name to filter annotations
            show_annotations: Whether to show object annotations, this will display the short_id of the object in the viewport you can use the short_id to select specific objects with the get_rhino_objects_with_metadata function
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
            result = await self.connection_manager.send_to_rhino(session_id, "capture_rhino_viewport", params)
            
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
            logger.error(f"Error capturing viewport from session {session_id}: {str(e)}")
            raise

    async def execute_rhino_code(self, ctx: Context, session_id: str, code: str) -> str:
        """Execute arbitrary Python code in Rhino.
        
        IMPORTANT NOTES FOR CODE EXECUTION:
        0. DONT FORGET NO f-strings! No f-strings, No f-strings!
        1. This is Rhino 7 with IronPython 2.7 - no f-strings or modern Python features
        3. When creating objects, ALWAYS call add_rhino_object_metadata(name, description) after creation
        4. For user interaction, you can use RhinoCommon syntax (selected_objects = rs.GetObjects("Please select some objects") etc.) prompted the user what to do 
           but prefer automated solutions unless user interaction is specifically requested
        5. Always show the user the code you are executing   
        
        The add_rhino_object_metadata() function is provided in the code context and must be called
        after creating any object. It adds standardized metadata including:
        - name (provided by you)
        - description (provided by you)
        The metadata helps you to identify and select objects later in the scene and stay organised.

        Common Syntax Errors to Avoid:
        2. No walrus operator (:=)
        3. No type hints
        4. No modern Python features (match/case, etc.)
        5. No list/dict comprehensions with multiple for clauses
        6. No assignment expressions in if/while conditions

        Example of proper object creation:
        <<<python
        # Create geometry
        cube_id = rs.AddBox(corners)
        # Add metadata - ALWAYS do this after creating an object
        add_rhino_object_metadata(cube_id, "My Cube", "A test cube created via MCP")

        >>>

        DONT FORGET NO f-strings! No f-strings, No f-strings!
        
        Args:
            session_id: The session ID of the connected Rhino instance
            code: Python code to execute in Rhino
            
        Returns:
            Execution result or error message
        """
        try:
            code_template = """
import rhinoscriptsyntax as rs
import scriptcontext as sc
import json
import time
from datetime import datetime

def add_rhino_object_metadata(obj_id, name=None, description=None):
    # Add standardized metadata to an object
    try:
        # Generate short ID
        short_id = datetime.now().strftime("%d%H%M%S")
        
        # Get bounding box
        bbox = rs.BoundingBox(obj_id)
        bbox_data = [[p.X, p.Y, p.Z] for p in bbox] if bbox else []
        
        # Get object type
        obj = sc.doc.Objects.Find(obj_id)
        obj_type = obj.Geometry.GetType().Name if obj else "Unknown"
        
        # Standard metadata
        metadata = {
            "short_id": short_id,
            "created_at": time.time(),
            "layer": rs.ObjectLayer(obj_id),
            "type": obj_type,
            "bbox": bbox_data
        }
        
        # User-provided metadata
        if name:
            rs.ObjectName(obj_id, name)
            metadata["name"] = name
        else:
            auto_name = "{0}_{1}".format(obj_type, short_id)
            rs.ObjectName(obj_id, auto_name)
            metadata["name"] = auto_name
            
        if description:
            metadata["description"] = description
            
        # Store metadata as user text
        user_text_data = metadata.copy()
        user_text_data["bbox"] = json.dumps(bbox_data)
        
        for key, value in user_text_data.items():
            rs.SetUserText(obj_id, key, str(value))
            
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

            """ + code
            
            logger.info(f"Sending code execution request to Rhino session {session_id}")
            result = await self.connection_manager.send_to_rhino(session_id, "execute_code", {"code": code_template})
            
            logger.info(f"Received response from Rhino session {session_id}: {result}")
            
            # Handle the response including printed output
            if result.get("status") == "error":
                error_msg = f"Error: {result.get('message', 'Unknown error')}"
                printed_output = result.get("printed_output", [])
                if printed_output:
                    error_msg += "\n\nPrinted output before error:\n" + "\n".join(printed_output)
                logger.error(f"Code execution error in session {session_id}: {error_msg}")
                return error_msg
            else:
                response = result.get("result", "Code executed successfully")
                printed_output = result.get("printed_output", [])
                if printed_output:
                    response += "\n\nPrinted output:\n" + "\n".join(printed_output)
                logger.info(f"Code execution successful in session {session_id}: {response}")
                return response
                
        except Exception as e:
            error_msg = f"Error executing code in session {session_id}: {str(e)}"
            logger.error(error_msg)
            return error_msg

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
            result = await self.connection_manager.send_to_rhino(session_id, "get_rhino_selected_objects", params)
            return json.dumps(result, indent=2)
        except Exception as e:
            logger.error(f"Error getting selected objects from Rhino session {session_id}: {str(e)}")
            return f"Error getting selected objects: {str(e)}"

    async def look_up_RhinoScriptSyntax(self, ctx: Context, function_name: str) -> str:
        """Look up the documentation for a RhinoScriptSyntax function.
        
        This tool fetches the detailed API documentation for a specified RhinoScriptSyntax function
        directly from the GitHub source code repository.
        
        Args:
            function_name: The name of the RhinoScriptSyntax function to look up
            
        Returns:
            str: The documentation for the function including signature, parameters, returns, and examples
        """
        try:
            # Get the category for the function
            category = get_function_category(function_name)
            if not category:
                return f"Function '{function_name}' not found in RhinoScriptSyntax categories"
            
            # Construct the URL to the GitHub repository source code 
            # the raw.githubusercontent.com/... gives raw source code
            github_url = f"https://raw.githubusercontent.com/mcneel/rhinoscriptsyntax/rhino-8.x/Scripts/rhinoscript/{category}.py"
            logger.info(f"Looking up documentation at URL: {github_url}")
            
            # Fetch the Python source file
            response = requests.get(github_url)
            if response.status_code != 200:
                return f"Failed to fetch source code for category '{category}' (HTTP status: {response.status_code})"
            
            # Parse the Python file to find the function definition and docstring
            source_code = response.text
            
            # Look for the function definition
            function_pattern = re.compile(f"def {function_name}\\s*\\(.*?\\):", re.DOTALL)
            function_match = function_pattern.search(source_code)
            if not function_match:
                return f"Function '{function_name}' not found in the source code for category '{category}'"
            
            # Find the start of the function
            function_start = function_match.start()
            
            # Extract the docstring
            docstring_start = source_code.find('"""', function_start)
            if docstring_start == -1:
                return f"No documentation found for function '{function_name}'"
            
            docstring_end = source_code.find('"""', docstring_start + 3)
            if docstring_end == -1:
                return f"Malformed documentation for function '{function_name}'"
            
            docstring = source_code[docstring_start + 3:docstring_end].strip()
            
            # Format the docstring into Markdown
            documentation = []
            
            # Add the function name as a header
            documentation.append(f"# {function_name}")
            documentation.append("")
            
            # Add the function signature
            function_def = function_match.group(0).strip()[4:-1]  # Remove 'def ' prefix and ':' suffix
            documentation.append("```python")
            documentation.append(function_def)
            documentation.append("```")
            documentation.append("")
            
            # Process the docstring into sections
            lines = docstring.split("\n")
            current_section = "Description"
            sections = {"Description": []}
            
            for line in lines:
                line = line.strip()
                # Remove leading spaces that might be part of the docstring formatting
                if line.startswith(" "):
                    line = line.lstrip()
                
                # Check if this is a section header
                if line.endswith(":") and not line.startswith(" "):
                    current_section = line[:-1]  # Remove the colon
                    if current_section not in sections:
                        sections[current_section] = []
                else:
                    sections[current_section].append(line)
            
            # Format each section
            for section, content in sections.items():
                if section == "Description" and content:
                    for line in content:
                        if line:
                            documentation.append(line)
                    documentation.append("")
                elif section == "Parameters" and content:
                    documentation.append(f"## {section}")
                    for line in content:
                        if line:
                            documentation.append(f"- {line}")
                    documentation.append("")
                elif section == "Returns" and content:
                    documentation.append(f"## {section}")
                    for line in content:
                        if line:
                            documentation.append(f"- {line}")
                    documentation.append("")
                elif section == "Example" and content:
                    documentation.append(f"## {section}")
                    # Find the start of code blocks
                    in_code_block = False
                    for line in content:
                        if not in_code_block and (line.strip().startswith("import") or line.strip().startswith("rs.")):
                            documentation.append("```python")
                            in_code_block = True
                        
                        if in_code_block and not line.strip() and "```" not in documentation[-1]:
                            documentation.append("```")
                            in_code_block = False
                        
                        documentation.append(line)
                    
                    if in_code_block:
                        documentation.append("```")
                    documentation.append("")
                elif section == "See Also" and content:
                    documentation.append(f"## {section}")
                    items = []
                    for line in content:
                        if line.strip():
                            items.append(line.strip())
                    
                    for item in items:
                        documentation.append(f"- {item}")
                    documentation.append("")
            
            # Add a link to the GitHub repository
            github_view_url = f"https://github.com/mcneel/rhinoscriptsyntax/blob/rhino-8.x/Scripts/rhinoscript/{category}.py"
            documentation.append(f"[View source code on GitHub]({github_view_url})")
            
            return "\n".join(documentation)
            
        except Exception as e:
            logger.error(f"Error looking up RhinoScriptSyntax documentation: {str(e)}")
            return f"Error fetching documentation: {str(e)}"