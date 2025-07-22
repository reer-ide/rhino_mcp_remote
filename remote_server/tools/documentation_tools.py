"""Documentation lookup tools for RhinoScript."""
import json
import re
import requests
from fastmcp import Context
from typing import Optional, Dict, Any
try:
    from ..connection_manager import ConnectionManager
    from ..utils.rhino_script_categories import get_function_category
except ImportError:
    from remote_server.connection_manager import ConnectionManager
    from remote_server.utils.rhino_script_categories import get_function_category
from remote_server.utils.tool_helpers import handle_error

def register_tools(mcp, connection_manager: ConnectionManager):
    """Register documentation tools with the MCP server."""
    
    @mcp.tool()
    async def look_up_RhinoScriptSyntax(session_id: str, function_name: str) -> str:
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
            return handle_error("looking up RhinoScriptSyntax documentation", "N/A", e)
