"""
Tests for the Remote Rhino MCP Server with enhanced functionality.
"""

import pytest
from fastmcp import Client
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
from datetime import datetime

from remote_server.server import mcp


@pytest.fixture
def mock_rhino_tools_connection_manager():
    """Mock the connection manager on the RhinoTools instance."""
    with patch('remote_server.server.rhino_tools.connection_manager') as mock_cm:
        # Setup async mock methods
        mock_cm.register_license = AsyncMock(return_value=MagicMock(
            license_id="test-license-123",
            user_id="user123",
            registered_at=datetime.now(),
            max_concurrent_files=3
        ))
        
        mock_cm.validate_license = AsyncMock(return_value=True)
        
        mock_cm.get_license = AsyncMock(return_value=MagicMock(
            license_id="test-license-123",
            user_id="user123",
            registered_at=datetime.now(),
            last_seen=datetime.now(),
            max_concurrent_files=3
        ))
        
        mock_cm.create_persistent_session = AsyncMock(return_value=MagicMock(
            session_id="test-session-123",
            status="pending",
            user_id="user123",
            file_path="/path/to/test.3dm"
        ))
        
        mock_cm.create_session = AsyncMock(return_value=MagicMock(
            session_id="test-session-legacy",
            status="pending",
            user_id="user123",
            file_path="/path/to/test.3dm"
        ))
        
        mock_cm.get_session = AsyncMock(return_value=MagicMock(
            session_id="test-session-123",
            status="active",
            user_id="user123",
            file_path="/path/to/test.3dm",
            created_at=datetime.now()
        ))
        
        mock_cm.get_active_sessions = AsyncMock(return_value=[])
        mock_cm.get_pending_sessions = AsyncMock(return_value=[])
        mock_cm.reactivate_session = AsyncMock(return_value=MagicMock(
            session_id="test-session-123",
            status="active"
        ))
        
        mock_cm.cleanup_expired_sessions = AsyncMock()
        
        # Mock send_to_rhino for ping responses
        mock_cm.send_to_rhino = AsyncMock(return_value={"status": "ok", "message": "pong"})
        
        yield mock_cm


class TestBasicMCPFunctionality:
    """Test basic MCP functionality."""

    @pytest.mark.asyncio
    async def test_ping_tool_mocked(self, mock_rhino_tools_connection_manager):
        """Test the ping tool functionality with mocked connection manager."""
        client = Client(mcp)
        
        async with client:
            # Ping tool requires session_id parameter
            result = await client.call_tool("ping", {"session_id": "test-session-123"})
            assert result.content[0].text == '{\n  "status": "ok",\n  "message": "pong"\n}'

    @pytest.mark.asyncio
    async def test_server_info_resource(self):
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
    async def test_list_tools(self):
        """Test listing available tools."""
        client = Client(mcp)
        
        async with client:
            tools = await client.list_tools()
            tool_names = [t.name for t in tools]
            assert "ping" in tool_names
            # Check for other Rhino tools
            assert "get_rhino_scene_info" in tool_names
            assert "execute_rhino_code" in tool_names


class TestConnectionManagerIntegration:
    """Test connection manager integration with mocked data."""

    @pytest.mark.asyncio
    async def test_mcp_server_with_tools(self, mock_rhino_tools_connection_manager):
        """Test that MCP server has the expected tools configured."""
        client = Client(mcp)
        
        async with client:
            tools = await client.list_tools()
            tool_names = [t.name for t in tools]
            
            # Check that basic tools are available
            assert "ping" in tool_names
            
            # Test ping tool works with session_id
            result = await client.call_tool("ping", {"session_id": "test-session-123"})
            assert result.content[0].text == '{\n  "status": "ok",\n  "message": "pong"\n}'

    @pytest.mark.asyncio
    async def test_mcp_server_resources(self, mock_rhino_tools_connection_manager):
        """Test that MCP server has the expected resources."""
        client = Client(mcp)
        
        async with client:
            resources = await client.list_resources()
            resource_uris = [str(r.uri) for r in resources]
            
            # Check that expected resources are available
            assert "server://info" in resource_uris
            
            # Test server info resource
            info = await client.read_resource("server://info")
            assert len(info) > 0
            info_text = info[0].text
            assert "remote-rhino-mcp-server" in info_text
            assert "version" in info_text
            assert "persistent sessions" in info_text.lower()

    @pytest.mark.asyncio
    async def test_rhino_tools_with_session(self, mock_rhino_tools_connection_manager):
        """Test that Rhino tools require session_id parameter."""
        client = Client(mcp)
        
        async with client:
            tools = await client.list_tools()
            
            # Find Rhino-specific tools (they should require session_id)
            rhino_tools = [t for t in tools if t.name not in ["ping"]]
            
            if rhino_tools:
                # Test that tools require session_id
                tool = rhino_tools[0]
                
                # This should fail without session_id
                try:
                    await client.call_tool(tool.name, {})
                    assert False, "Tool should require session_id"
                except Exception as e:
                    # Expected to fail without session_id
                    assert "session_id" in str(e).lower() or "required" in str(e).lower()

    @pytest.mark.asyncio
    async def test_get_rhino_scene_info_tool(self, mock_rhino_tools_connection_manager):
        """Test the get_rhino_scene_info tool."""
        # Mock the scene info response
        mock_rhino_tools_connection_manager.send_to_rhino.return_value = {
            "layers": ["Default", "Layer01"],
            "objects": [{"id": "obj1", "type": "Point"}]
        }
        
        client = Client(mcp)
        
        async with client:
            result = await client.call_tool("get_rhino_scene_info", {"session_id": "test-session-123"})
            assert "layers" in result.content[0].text
            assert "objects" in result.content[0].text


class TestServerConfiguration:
    """Test server configuration and setup."""

    def test_server_name_and_instructions(self):
        """Test that server has correct name and instructions."""
        assert mcp.name == "remote-rhino-mcp-server"
        assert "rhino" in mcp.instructions.lower()
        assert "session_id" in mcp.instructions.lower()

    @pytest.mark.asyncio
    async def test_server_has_tools_configured(self, mock_rhino_tools_connection_manager):
        """Test that server has tools configured properly."""
        client = Client(mcp)
        async with client:
            tools = await client.list_tools()
            tool_names = [t.name for t in tools]
            
            # Check that expected tools are available
            assert "ping" in tool_names
            assert "get_rhino_scene_info" in tool_names
            assert "execute_rhino_code" in tool_names
            
            # Basic connectivity test with proper session_id
            result = await client.call_tool("ping", {"session_id": "test-session-123"})
            assert result.content[0].text == '{\n  "status": "ok",\n  "message": "pong"\n}'


class TestMockValidation:
    """Test that our mocking setup works correctly."""

    @pytest.mark.asyncio
    async def test_connection_manager_mock_setup(self, mock_rhino_tools_connection_manager):
        """Test that connection manager mocking is working."""
        # Test license methods
        license_result = await mock_rhino_tools_connection_manager.register_license(
            "test-license", "user123", "machine123"
        )
        assert license_result.license_id == "test-license-123"
        
        # Test validation
        is_valid = await mock_rhino_tools_connection_manager.validate_license(
            "test-license-123", "machine123"
        )
        assert is_valid is True
        
        # Test session creation
        session_result = await mock_rhino_tools_connection_manager.create_persistent_session(
            "user123", "/path/to/test.3dm", "test-license-123"
        )
        assert session_result.session_id == "test-session-123"
        
        # Test send_to_rhino method
        rhino_result = await mock_rhino_tools_connection_manager.send_to_rhino(
            "test-session-123", "ping"
        )
        assert rhino_result["status"] == "ok"
        assert rhino_result["message"] == "pong"


class TestRhinoToolsIntegration:
    """Test Rhino tools integration with mocked responses."""

    @pytest.mark.asyncio
    async def test_execute_rhino_code_tool(self, mock_rhino_tools_connection_manager):
        """Test the execute_rhino_code tool."""
        # Mock the code execution response
        mock_rhino_tools_connection_manager.send_to_rhino.return_value = {
            "status": "success",
            "result": "Code executed successfully",
            "printed_output": ["Hello from Rhino!"]
        }
        
        client = Client(mcp)
        
        async with client:
            result = await client.call_tool("execute_rhino_code", {
                "session_id": "test-session-123",
                "code": "print('Hello from Rhino!')"
            })
            assert "Code executed successfully" in result.content[0].text
            assert "Hello from Rhino!" in result.content[0].text

    @pytest.mark.asyncio
    async def test_get_rhino_layers_tool(self, mock_rhino_tools_connection_manager):
        """Test the get_rhino_layers tool."""
        # Mock the layers response
        mock_rhino_tools_connection_manager.send_to_rhino.return_value = {
            "layers": [
                {"name": "Default", "visible": True},
                {"name": "Layer01", "visible": False}
            ]
        }
        
        client = Client(mcp)
        
        async with client:
            result = await client.call_tool("get_rhino_layers", {"session_id": "test-session-123"})
            assert "Default" in result.content[0].text
            assert "Layer01" in result.content[0].text

    @pytest.mark.asyncio
    async def test_look_up_rhinoscriptsyntax_tool(self):
        """Test the look_up_RhinoScriptSyntax tool (doesn't need connection manager)."""
        client = Client(mcp)
        
        async with client:
            # This tool doesn't require a connection manager, just makes HTTP requests
            result = await client.call_tool("look_up_RhinoScriptSyntax", {
                "function_name": "AddPoint"
            })
            # Should contain documentation or error message
            assert len(result.content[0].text) > 0


class TestSimpleConnectivity:
    """Test simple server connectivity without mocking."""

    @pytest.mark.asyncio
    async def test_basic_server_connectivity(self):
        """Test basic server connectivity without external dependencies."""
        client = Client(mcp)
        
        async with client:
            # Test resources (should work without Rhino connection)
            resources = await client.list_resources()
            assert len(resources) > 0
            
            # Test tools list (should work without Rhino connection)
            tools = await client.list_tools()
            assert len(tools) > 0
            
            # Test server info resource
            info = await client.read_resource("server://info")
            assert len(info) > 0
            assert "remote-rhino-mcp-server" in info[0].text

    @pytest.mark.asyncio
    async def test_tools_without_active_sessions(self):
        """Test that tools fail gracefully when no active sessions exist."""
        client = Client(mcp)
        
        async with client:
            # Test that tools fail gracefully without active sessions
            result = await client.call_tool("ping", {"session_id": "nonexistent-session"})
            assert "No active connection" in result.content[0].text or "Error" in result.content[0].text


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 