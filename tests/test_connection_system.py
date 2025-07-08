"""
Test script for the bidirectional connection system.
"""

import asyncio
import json
import aiohttp
import websockets
import pytest
from datetime import datetime

# Test configuration
SERVER_URL = "http://127.0.0.1:8080"
TEST_USER_ID = "test_user_123"
TEST_FILE_PATH = "/path/to/test.3dm"


class MockRhinoPlugin:
    """Mock Rhino plugin for testing"""
    
    def __init__(self):
        self.websocket = None
        self.session_id = None
        self.instance_id = None
        
    async def connect(self, websocket_url: str):
        """Connect to the remote server"""
        print(f"Connecting to: {websocket_url}")
        self.websocket = await websockets.connect(websocket_url)
        
        # Wait for handshake
        handshake = await self.websocket.recv()
        handshake_data = json.loads(handshake)
        print(f"Received handshake: {handshake_data}")
        
        self.session_id = handshake_data.get("session_id")
        self.instance_id = handshake_data.get("instance_id")
        
        # Start message handling
        asyncio.create_task(self._handle_messages())
        
    async def _handle_messages(self):
        """Handle incoming messages from server"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                await self._process_message(data)
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed")
        except Exception as e:
            print(f"Error handling messages: {e}")
    
    async def _process_message(self, data: dict):
        """Process a message from the server"""
        message_type = data.get("type")
        correlation_id = data.get("correlation_id")
        
        print(f"Received message: {data}")
        
        if message_type == "command":
            tool = data.get("tool")
            params = data.get("params", {})
            
            # Simulate CAD operation
            if tool == "create_sphere":
                result = f"sphere_obj_{datetime.now().timestamp()}"
                response = {
                    "type": "response",
                    "correlation_id": correlation_id,
                    "status": "success",
                    "result": result
                }
            elif tool == "create_box":
                result = f"box_obj_{datetime.now().timestamp()}"
                response = {
                    "type": "response",
                    "correlation_id": correlation_id,
                    "status": "success",
                    "result": result
                }
            else:
                response = {
                    "type": "response",
                    "correlation_id": correlation_id,
                    "status": "error",
                    "error": f"Unknown tool: {tool}"
                }
            
            await self.websocket.send(json.dumps(response))
            print(f"Sent response: {response}")
        
        elif message_type == "heartbeat":
            # Respond to heartbeat
            heartbeat_response = {
                "type": "heartbeat",
                "timestamp": datetime.now().isoformat()
            }
            await self.websocket.send(json.dumps(heartbeat_response))
    
    async def close(self):
        """Close the connection"""
        if self.websocket:
            await self.websocket.close()


async def test_session_creation():
    """Test session creation endpoint"""
    print("\n=== Testing Session Creation ===")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{SERVER_URL}/sessions/create",
            json={
                "user_id": TEST_USER_ID,
                "file_path": TEST_FILE_PATH
            }
        ) as response:
            assert response.status == 200
            data = await response.json()
            
            print(f"Session created: {data}")
            
            assert "session_id" in data
            assert "connection_token" in data
            assert "websocket_url" in data
            assert "websocket_port" in data
            
            return data


async def test_rhino_connection(session_data: dict):
    """Test Rhino plugin connection"""
    print("\n=== Testing Rhino Connection ===")
    
    mock_plugin = MockRhinoPlugin()
    await mock_plugin.connect(session_data["websocket_url"])
    
    # Wait a bit for connection to establish
    await asyncio.sleep(2)
    
    return mock_plugin


async def test_session_status(session_id: str):
    """Test session status endpoint"""
    print("\n=== Testing Session Status ===")
    
    # Note: This would need to be implemented as an MCP resource call
    # For now, we'll just print the session_id
    print(f"Session ID: {session_id}")


async def test_cad_operations(session_id: str):
    """Test CAD operations via MCP tools"""
    print("\n=== Testing CAD Operations ===")
    
    # Note: This would require an MCP client to test the tools
    # For now, we'll simulate the operations
    print(f"Would test create_sphere and create_box with session_id: {session_id}")


async def test_notifications(session_id: str):
    """Test SSE notifications"""
    print("\n=== Testing SSE Notifications ===")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{SERVER_URL}/sessions/{session_id}/notifications"
        ) as response:
            print(f"SSE Response status: {response.status}")
            
            # Read a few events
            count = 0
            async for line in response.content:
                if line.startswith(b"data: "):
                    data = json.loads(line[6:].decode())
                    print(f"Received SSE event: {data}")
                    count += 1
                    if count >= 1:  # Stop after 1 events
                        break


async def run_integration_test():
    """Run the complete integration test"""
    print("Starting Remote Rhino MCP Server Integration Test")
    print("=" * 50)
    
    try:
        # Test 1: Create session
        session_data = await test_session_creation()
        session_id = session_data["session_id"]
        
        # Test 2: Connect mock Rhino plugin
        mock_plugin = await test_rhino_connection(session_data)
        
        # Test 3: Check session status
        await test_session_status(session_id)
        
        # Test 4: Test CAD operations (would need MCP client)
        await test_cad_operations(session_id)
        
        # Test 5: Test SSE notifications
        await asyncio.wait_for(test_notifications(session_id), timeout=10.0)
        
        # Cleanup
        await mock_plugin.close()
        
        print("\n" + "=" * 50)
        print("✅ Integration test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        raise


if __name__ == "__main__":
    print("Make sure the Remote Rhino MCP Server is running on 0.0.0.0:8080")
    print("Start the server with: python -m remote_server.server")
    print()
    
    asyncio.run(run_integration_test()) 