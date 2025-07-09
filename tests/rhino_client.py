"""
Rhino Test Client - Connects to the Remote MCP Server
"""

import asyncio
import aiohttp
import websockets
import json
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SERVER_URL = "http://127.0.0.1:8080"

class RhinoTestClient:
    """A test client that mimics the Rhino plugin's behavior."""
    
    def __init__(self, server_url: str):
        self.server_url = server_url
        self.session_data: Dict[str, Any] = {}
        self.websocket: websockets.WebSocketClientProtocol = None

    async def run(self):
        """Run the test client."""
        try:
            await self.create_session()
            await self.connect_websocket()
            await self.listen_for_commands()
        except Exception as e:
            logger.error(f"Client run failed: {e}")
        finally:
            if self.websocket:
                await self.websocket.close()
            logger.info("Client shutdown.")

    async def create_session(self):
        """Create a new session with the server."""
        logger.info("Creating session...")
        url = f"{self.server_url}/sessions/create"
        payload = {"user_id": "test_client_user", "file_path": "test.3dm"}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                response.raise_for_status()
                self.session_data = await response.json()
                logger.info(f"Session created: {self.session_data['session_id']}")

    async def connect_websocket(self):
        """Connect to the WebSocket server."""
        websocket_url = self.session_data.get("websocket_url")
        if not websocket_url:
            raise ValueError("WebSocket URL not found in session data.")
            
        logger.info(f"Connecting to WebSocket: {websocket_url}")
        self.websocket = await websockets.connect(websocket_url)
        logger.info("WebSocket connection established.")
        
        # Wait for handshake message from server
        handshake_message = await self.websocket.recv()
        handshake = json.loads(handshake_message)
        logger.info(f"Received handshake: {handshake}")

    async def listen_for_commands(self):
        """Listen for commands from the server and process them."""
        logger.info("Listening for commands...")
        async for message in self.websocket:
            command = json.loads(message)
            logger.info(f"Received command: {command}")
            
            response = await self.execute_command(command)
            
            logger.info(f"Sending response: {response}")
            await self.websocket.send(json.dumps(response))

    async def execute_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a command and return a response."""
        tool = command.get("tool")
        params = command.get("params", {})
        correlation_id = command.get("correlation_id")
        
        response = {
            "type": "response",
            "correlation_id": correlation_id,
            "status": "success",
            "result": None,
        }
        
        # Mock implementations of Rhino tools
        if tool == "get_rhino_scene_info":
            response["result"] = {"layers": [{"name": "Default", "object_count": 5}]}
        elif tool == "get_rhino_layers":
            response["result"] = {"layers": [{"name": "Default"}]}
        elif tool == "execute_code":
            response["result"] = "Code executed successfully (mock)."
            response["printed_output"] = ["print output 1", "print output 2"]
        else:
            response["status"] = "error"
            response["message"] = f"Unknown tool: {tool}"
            
        return response

async def main():
    """Main entry point for the test client."""
    client = RhinoTestClient(SERVER_URL)
    await client.run()

if __name__ == "__main__":
    logger.info("Starting Rhino Test Client...")
    logger.info("Make sure the Remote Rhino MCP Server is running.")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Client interrupted.") 