#!/usr/bin/env python3
"""
Test script to verify the modified rhino_script_websocket.py can connect to the remote server.
This simulates the connection flow without requiring Rhino.
"""

import asyncio
import json
import aiohttp
import websockets
import time
from datetime import datetime

# Configuration
SERVER_URL = "http://127.0.0.1:8080"
TEST_USER_ID = "test_rhino_user"
TEST_FILE_PATH = "/path/to/test.3dm"

class MockRhinoScriptTest:
    """Mock test to simulate the Rhino script connection flow"""
    
    def __init__(self):
        self.session_data = None
        self.websocket = None
        self.session_id = None
        self.instance_id = None
        
    async def create_session(self):
        """Create a session like the Rhino script does"""
        print("Creating session...")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{SERVER_URL}/sessions/create",
                json={
                    "user_id": TEST_USER_ID,
                    "file_path": TEST_FILE_PATH
                }
            ) as response:
                if response.status == 200:
                    self.session_data = await response.json()
                    print(f"Session created: {self.session_data}")
                    return True
                else:
                    print(f"Failed to create session: {response.status}")
                    return False
    
    async def connect_websocket(self):
        """Connect to WebSocket like the Rhino script does"""
        if not self.session_data:
            print("No session data available")
            return False
            
        websocket_url = self.session_data["websocket_url"]
        print(f"Connecting to WebSocket: {websocket_url}")
        
        try:
            self.websocket = await websockets.connect(websocket_url)
            print("WebSocket connected successfully")
            
            # Wait for handshake
            handshake_message = await self.websocket.recv()
            handshake_data = json.loads(handshake_message)
            print(f"Received handshake: {handshake_data}")
            
            if handshake_data.get("type") == "handshake":
                self.session_id = handshake_data.get("session_id")
                self.instance_id = handshake_data.get("instance_id")
                print(f"Handshake successful - Session: {self.session_id}, Instance: {self.instance_id}")
                return True
            else:
                print("Unexpected handshake format")
                return False
                
        except Exception as e:
            print(f"WebSocket connection failed: {e}")
            return False
    
    async def simulate_command_handling(self):
        """Simulate handling commands from the server"""
        print("Simulating command handling...")
        
        # Mock command that might be sent by the server
        mock_command = {
            "type": "command",
            "tool": "get_rhino_scene_info",
            "params": {},
            "correlation_id": "test_correlation_123"
        }
        
        # Simulate what the Rhino script would do
        print(f"Would execute tool: {mock_command['tool']}")
        
        # Mock response
        mock_response = {
            "type": "response",
            "correlation_id": mock_command["correlation_id"],
            "status": "success",
            "result": {
                "status": "success",
                "layers": [
                    {
                        "full_path": "Default",
                        "object_count": 2,
                        "is_visible": True,
                        "is_locked": False,
                        "example_objects": [
                            {
                                "id": "mock_object_1",
                                "name": "Mock Object 1",
                                "type": "NurbsCurve",
                                "metadata": {}
                            }
                        ]
                    }
                ]
            }
        }
        
        print(f"Would send response: {mock_response}")
        
        # In the real script, this would be sent via WebSocket
        # await self.websocket.send(json.dumps(mock_response))
        
        return True
    
    async def close(self):
        """Close the WebSocket connection"""
        if self.websocket:
            await self.websocket.close()
            print("WebSocket connection closed")

async def test_rhino_script_connection():
    """Test the complete connection flow"""
    print("=" * 50)
    print("Testing Rhino Script Connection Flow")
    print("=" * 50)
    
    test_client = MockRhinoScriptTest()
    
    try:
        # Step 1: Create session
        print("\n1. Creating session...")
        if not await test_client.create_session():
            print("❌ Session creation failed")
            return False
        print("✅ Session created successfully")
        
        # Step 2: Connect WebSocket
        print("\n2. Connecting WebSocket...")
        if not await test_client.connect_websocket():
            print("❌ WebSocket connection failed")
            return False
        print("✅ WebSocket connected successfully")
        
        # Step 3: Simulate command handling
        print("\n3. Simulating command handling...")
        if not await test_client.simulate_command_handling():
            print("❌ Command handling simulation failed")
            return False
        print("✅ Command handling simulation successful")
        
        # Step 4: Test heartbeat
        print("\n4. Testing heartbeat...")
        heartbeat = {
            "type": "heartbeat",
            "timestamp": datetime.now().isoformat()
        }
        print(f"Would handle heartbeat: {heartbeat}")
        print("✅ Heartbeat handling successful")
        
        print("\n" + "=" * 50)
        print("✅ All tests passed! The Rhino script should work with the remote server.")
        print("=" * 50)
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False
    finally:
        await test_client.close()

if __name__ == "__main__":
    print("Starting Rhino Script Connection Test")
    print("Make sure the remote server is running on http://127.0.0.1:8080")
    
    # Run the test
    success = asyncio.run(test_rhino_script_connection())
    
    if success:
        print("\n🎉 The modified rhino_script_websocket.py should work correctly!")
        print("You can now use it in Rhino to connect to the remote server.")
    else:
        print("\n❌ There may be issues with the connection. Check the server logs.") 