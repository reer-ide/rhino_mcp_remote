"""
Tests for the Remote Rhino MCP Server.
"""

import pytest
from fastmcp import Client

from remote_server.server import mcp


@pytest.mark.asyncio
async def test_ping_tool():
    """Test the ping tool functionality."""
    client = Client(mcp)
    
    async with client:
        result = await client.call_tool("ping", {})
        assert result.content[0].text == "pong"


@pytest.mark.asyncio
async def test_server_info_resource():
    """Test the server info resource."""
    client = Client(mcp)
    
    async with client:
        resources = await client.list_resources()
        resource_uris = [str(r.uri) for r in resources]
        assert "server://info" in resource_uris
        
        info = await client.read_resource("server://info")
        assert len(info) > 0
        assert "remote-rhino-mcp-server" in info[0].text


@pytest.mark.asyncio
async def test_list_tools():
    """Test listing available tools."""
    client = Client(mcp)
    
    async with client:
        tools = await client.list_tools()
        tool_names = [t.name for t in tools]
        assert "ping" in tool_names 