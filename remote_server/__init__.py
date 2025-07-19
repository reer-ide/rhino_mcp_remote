"""
Remote Rhino MCP Server

A FastMCP-based server for remote Rhino CAD integration.
"""
 
__version__ = "0.1.0" 

from .server import mcp, logger, connection_manager

__all__ = [
    "mcp",
]