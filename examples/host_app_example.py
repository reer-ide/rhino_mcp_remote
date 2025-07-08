"""
Example host application integration with Remote Rhino MCP Server.

This demonstrates how a host application (like reer's IDE) would integrate
with the remote MCP server to establish connections with Rhino instances.
"""

import asyncio
import aiohttp
import json
from typing import Optional, Dict, Any
from datetime import datetime


class RhinoConnector:
    """
    Connector class for integrating with Remote Rhino MCP Server.
    
    This class handles the complete flow:
    1. Create connection session
    2. Initiate Rhino plugin connection
    3. Monitor connection status via SSE
    4. Execute CAD operations via MCP tools
    """
    
    def __init__(self, server_url: str = "http://localhost:8080"):
        self.server_url = server_url
        self.session_data: Optional[Dict] = None
        self.connection_established = False
        
    async def link_rhino_file(self, user_id: str, file_path: str) -> Dict[str, Any]:
        """
        Initiate connection with a Rhino file.
        
        This simulates the UX flow:
        1. User selects Rhino file in host app
        2. Host app creates connection session
        3. Host app calls Rhino plugin to establish connection
        4. Connection is established and ready for CAD operations
        """
        try:
            print(f"🔗 Linking Rhino file: {file_path}")
            print(f"👤 User: {user_id}")
            
            # Step 1: Create connection session
            session_data = await self._create_session(user_id, file_path)
            self.session_data = session_data
            
            print(f"✅ Session created: {session_data['session_id']}")
            print(f"🔌 WebSocket URL: {session_data['websocket_url']}")
            
            # Step 2: Call Rhino plugin to establish connection
            # In real implementation, this would communicate with local Rhino plugin
            print(f"📞 Calling Rhino plugin to establish connection...")
            connection_result = await self._simulate_rhino_plugin_call(session_data)
            
            if connection_result["success"]:
                # Step 3: Wait for connection establishment
                print(f"⏳ Waiting for connection establishment...")
                await self._wait_for_connection(session_data["session_id"])
                
                self.connection_established = True
                print(f"🎉 Connection established successfully!")
                
                return {
                    "success": True,
                    "session_id": session_data["session_id"],
                    "message": "Rhino file linked successfully"
                }
            else:
                return {
                    "success": False,
                    "error": connection_result["error"]
                }
                
        except Exception as e:
            print(f"❌ Error linking Rhino file: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _create_session(self, user_id: str, file_path: str) -> Dict:
        """Create a new connection session with the remote server."""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.server_url}/sessions/create",
                json={
                    "user_id": user_id,
                    "file_path": file_path
                }
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Failed to create session: {error_text}")
                
                return await response.json()
    
    async def _simulate_rhino_plugin_call(self, session_data: Dict) -> Dict:
        """
        Simulate calling the Rhino plugin to establish connection.
        
        In real implementation, this would:
        1. Call local Rhino plugin via HTTP/COM/etc.
        2. Pass connection details to plugin
        3. Plugin shows authorization UI to user
        4. Plugin establishes WebSocket connection to remote server
        """
        # Simulate the call
        print(f"   📋 Connection Token: {session_data['connection_token'][:8]}...")
        print(f"   🔗 WebSocket Port: {session_data['websocket_port']}")
        print(f"   ⏰ Expires: {session_data['expires_at']}")
        
        # Simulate user authorization
        print(f"   🔐 User authorization required...")
        await asyncio.sleep(1)  # Simulate user interaction time
        
        print(f"   ✅ User authorized connection")
        
        # In real implementation, this would return the actual result
        # from the Rhino plugin
        return {
            "success": True,
            "message": "Plugin connection initiated"
        }
    
    async def _wait_for_connection(self, session_id: str, timeout: float = 30.0):
        """Wait for connection establishment via SSE notifications."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.server_url}/sessions/{session_id}/notifications"
                ) as response:
                    
                    start_time = asyncio.get_event_loop().time()
                    
                    async for line in response.content:
                        if line.startswith(b"data: "):
                            data = json.loads(line[6:].decode())
                            event_type = data.get("type")
                            
                            print(f"   📡 SSE Event: {event_type}")
                            
                            if event_type == "connection_established":
                                print(f"   🔗 Rhino instance connected: {data.get('instance_id', 'unknown')}")
                                return
                            elif event_type == "connection_error":
                                raise Exception(f"Connection failed: {data.get('data', {}).get('error', 'Unknown error')}")
                        
                        # Check timeout
                        if asyncio.get_event_loop().time() - start_time > timeout:
                            raise TimeoutError("Timeout waiting for connection establishment")
                            
        except asyncio.TimeoutError:
            raise TimeoutError("Timeout waiting for connection establishment")
    
    async def create_sphere(self, radius: float) -> Dict[str, Any]:
        """Create a sphere in the connected Rhino instance."""
        if not self.connection_established or not self.session_data:
            return {
                "success": False,
                "error": "No active Rhino connection"
            }
        
        # Note: In real implementation, this would use an MCP client
        # to call the create_sphere tool with the session_id parameter
        print(f"🔵 Creating sphere with radius {radius}")
        print(f"   📋 Session: {self.session_data['session_id']}")
        
        # Simulate the MCP tool call
        await asyncio.sleep(0.5)  # Simulate processing time
        
        return {
            "success": True,
            "result": f"sphere_obj_{datetime.now().timestamp()}",
            "message": f"Sphere created with radius {radius}"
        }
    
    async def create_box(self, width: float, height: float, depth: float) -> Dict[str, Any]:
        """Create a box in the connected Rhino instance."""
        if not self.connection_established or not self.session_data:
            return {
                "success": False,
                "error": "No active Rhino connection"
            }
        
        print(f"📦 Creating box {width}x{height}x{depth}")
        print(f"   📋 Session: {self.session_data['session_id']}")
        
        # Simulate the MCP tool call
        await asyncio.sleep(0.5)  # Simulate processing time
        
        return {
            "success": True,
            "result": f"box_obj_{datetime.now().timestamp()}",
            "message": f"Box created with dimensions {width}x{height}x{depth}"
        }
    
    async def get_connection_status(self) -> Dict[str, Any]:
        """Get the current connection status."""
        if not self.session_data:
            return {
                "connected": False,
                "message": "No session"
            }
        
        # Note: In real implementation, this would call the MCP resource
        # sessions/{session_id}/status
        return {
            "connected": self.connection_established,
            "session_id": self.session_data["session_id"],
            "file_path": "Simulated file path",
            "message": "Connection active" if self.connection_established else "Connection pending"
        }


async def demo_host_app():
    """Demonstrate the host application integration."""
    print("🚀 Remote Rhino MCP Server - Host App Demo")
    print("=" * 50)
    
    connector = RhinoConnector()
    
    try:
        # Step 1: Link Rhino file (simulates user selecting file)
        result = await connector.link_rhino_file(
            user_id="demo_user_123",
            file_path="/path/to/demo_project.3dm"
        )
        
        if not result["success"]:
            print(f"❌ Failed to link Rhino file: {result['error']}")
            return
        
        print(f"\n📊 Connection Status:")
        status = await connector.get_connection_status()
        for key, value in status.items():
            print(f"   {key}: {value}")
        
        # Step 2: Perform CAD operations
        print(f"\n🔧 Performing CAD Operations:")
        
        # Create a sphere
        sphere_result = await connector.create_sphere(5.0)
        print(f"   🔵 Sphere: {sphere_result}")
        
        # Create a box
        box_result = await connector.create_box(10.0, 8.0, 6.0)
        print(f"   📦 Box: {box_result}")
        
        print(f"\n✅ Demo completed successfully!")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")


if __name__ == "__main__":
    print("Host App Example for Remote Rhino MCP Server")
    print("Make sure the Remote Rhino MCP Server is running on localhost:8080")
    print("Start the server with: python -m remote_server.server")
    print()
    
    asyncio.run(demo_host_app()) 