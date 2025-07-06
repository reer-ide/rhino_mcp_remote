"""
Main FastMCP server for Remote Rhino CAD integration.
"""

import logging
from datetime import datetime
from typing import Dict, Any

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from .config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastMCP server instance
mcp = FastMCP(
    name = "remote-rhino-mcp-server",
    instructions= """
        This is a remote MCP server for Rhino(by Robert McNeel & Associates).
        It is used to connect to a user's local Rhino CAD instance and perform operations on it.
        """,
    )


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint for load balancers and monitoring."""
    return JSONResponse({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "server": "remote-rhino-mcp-server",
        "version": "0.1.0"
    })


@mcp.tool
def ping() -> str:
    """Simple ping tool for testing connectivity."""
    logger.info("Ping tool called")
    return "pong"


@mcp.resource("server://info")
def server_info() -> str:
    """Get server information and status."""
    info = {
        "name": "remote-rhino-mcp-server",
        "version": "0.1.0",
        "description": "Remote MCP server for Rhino CAD integration",
        "timestamp": datetime.now().isoformat(),
        "settings": {
            "host": settings.host,
            "port": settings.port,
            "debug": settings.debug,
        }
    }
    return str(info)


def main():
    """Main entry point for the server."""
    logger.info(f"Starting Remote Rhino MCP Server on {settings.host}:{settings.port}")
    
    mcp.run(
        transport="http",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level
    )


if __name__ == "__main__":
    main() 