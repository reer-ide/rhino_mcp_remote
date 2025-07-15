"""Tool registry for managing Rhino MCP tools."""
import importlib
import logging
from typing import Dict, Any
from remote_server.connection_manager import ConnectionManager

logger = logging.getLogger("RhinoTools")


class ToolRegistry:
    """Registry for managing and auto-registering Rhino MCP tools."""
    
    def __init__(self, app, connection_manager: ConnectionManager):
        self.app = app
        self.connection_manager = connection_manager
        self.tools = {}
    
    def register_all_tools(self):
        """Register all tools with the MCP server."""
        tool_modules = [
            'metadata_tools',
            'scene_tools', 
            'object_tools',
            'layer_tools',
            'viewport_tools',
            'execution_tools',
            'selection_tools',
            'documentation_tools',
            'utility_tools'
        ]
        
        for module_name in tool_modules:
            try:
                module = importlib.import_module(f'remote_server.tools.{module_name}')
                if hasattr(module, 'register_tools'):
                    module.register_tools(self.app, self.connection_manager)
                    logger.info(f"Registered tools from {module_name}")
                else:
                    logger.warning(f"Module {module_name} has no register_tools function")
            except ImportError as e:
                logger.error(f"Failed to import tool module {module_name}: {e}")
            except Exception as e:
                logger.error(f"Error registering tools from {module_name}: {e}")
        
        logger.info("Tool registration completed") 