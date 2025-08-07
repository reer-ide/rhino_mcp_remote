"""
Session management functionality for integration tests
"""

import asyncio
import aiohttp
import os
import sys
from typing import Dict, Any, Optional, List

# Handle both relative import (when run as module) and direct import (when run standalone)
try:
    from .base_tester import BaseIntegrationTester
except ImportError:
    # If relative import fails, we're running standalone
    # Add the current directory to path and import directly
    sys.path.insert(0, os.path.dirname(__file__))
    from base_tester import BaseIntegrationTester


class SessionTester(BaseIntegrationTester):
    """Handles session creation and management for tests"""
    
    async def create_host_session(self) -> bool:
        """Create a session as host application (simulating host app behavior)"""
        if not self.license_data:
            print("❌ No license data available for session creation")
            return False
        
        try:
            # Multi-file test configuration
            print("\n" + "="*70)
            print("📁 MULTI-FILE TEST CONFIGURATION")
            print("="*70)
            print("This test can run in two modes:")
            print("1. Single file test - Test one file only")
            print("2. Multi-file test - Test two files simultaneously to verify multi-process behavior")
            print()
            print("Available test files:")
            print("  • test_multi_storey.3dm - Sample file with geometry")
            print("  • test_empty.3dm - Empty file for testing")
            print("  • Custom file path")
            print()
            
            while True:
                mode = input("Choose test mode (1=single, 2=multi): ").strip()
                if mode in ['1', '2']:
                    break
                print("❌ Please enter '1' for single file or '2' for multi-file test.")
            
            test_files = []
            
            if mode == '1':
                # Single file mode
                print("\nSingle file mode selected.")
                file_path = await self.get_test_file_path("Enter the full path to your test .3dm file: ")
                test_files.append(file_path)
            else:
                # Multi-file mode
                print("\nMulti-file mode selected - this will test two files simultaneously.")
                print("This verifies that each Rhino file runs in a separate process with separate plugin instances.")
                print()
                
                # Get first file
                print("First test file:")
                file1 = await self.get_test_file_path("Enter path to first test file: ", 
                    "C:/Users/Zhish/OneDrive/GitHub/reer-rhino-mcp-plugin/tests/test_multi_storey.3dm")
                test_files.append(file1)
                
                # Get second file
                print("\nSecond test file:")
                file2 = await self.get_test_file_path("Enter path to second test file: ",
                    "C:/Users/Zhish/OneDrive/GitHub/reer-rhino-mcp-plugin/tests/test_empty.3dm")
                test_files.append(file2)
            
            # Store test files for later use
            self.test_files = test_files
            
            # Create sessions for all test files
            self.session_data_list = []
            
            for i, current_file in enumerate(test_files):
                print(f"\n🔄 Creating session {i+1}/{len(test_files)} for: {current_file}")
                
                session_request = {
                    "user_id": self.test_user_id,
                    "file_path": current_file,
                    "license_id": self.license_data['license_id']
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.server_url}/sessions/create", 
                        json=session_request
                    ) as response:
                        if response.status == 200:
                            session_data = await response.json()
                            self.session_data_list.append(session_data)
                            print(f"✅ Session {i+1} created successfully")
                            print(f"   Session ID: {session_data['session_id']}")
                            print(f"   File Path: {session_data['file_path']}")
                            print(f"   WebSocket URL: {session_data['websocket_url']}")
                        else:
                            error_data = await response.json()
                            print(f"❌ Session {i+1} creation failed: {error_data.get('error', 'Unknown error')}")
                            return False
            
            # Set primary session data for backward compatibility
            self.session_data = self.session_data_list[0] if self.session_data_list else None
            
            print(f"\n🎉 Created {len(self.session_data_list)} session(s) successfully!")
            return True
        except Exception as e:
            print(f"❌ Error creating host session: {e}")
            return False
    
    def prompt_user_plugin_connection(self) -> bool:
        """Guide user through plugin connection in Rhino"""
        if not self.session_data_list:
            print("❌ No session data available for connection")
            return False
        
        print("\n" + "="*80)
        print("🔌 USER ACTION REQUIRED: Plugin Connection")
        print("="*80)
        print()
        
        if len(self.session_data_list) == 1:
            # Single file instructions
            print("Please perform the following steps in Rhino:")
            print()
            print("1. Open the test file in Rhino:")
            print(f"   {self.session_data_list[0]['file_path']}")
            print()
            print("2. Run the following command:")
            print("   ReerStart --> Remote")
            print()
            print("3. The plugin should automatically connect to the existing session")
            print()
        else:
            # Multi-file instructions
            print("Multi-file test - Please perform the following steps:")
            print()
            for i, session_data in enumerate(self.session_data_list):
                print(f"--- File {i+1} ---")
                print(f"1. Open a new instance of Rhino")
                print(f"2. Open the test file:")
                print(f"   {session_data['file_path']}")
                print(f"3. Run: ReerStart --> Remote")
                print(f"4. The plugin should connect to session: {session_data['session_id'][:8]}...")
                print()
        
        while True:
            user_input = input("✅ Plugin connection(s) established? (y/n): ").strip().lower()
            if user_input in ['y', 'yes']:
                return True
            elif user_input in ['n', 'no']:
                print("❌ Plugin connection not established. Please try again.")
                return False
            else:
                print("Please enter 'y' for yes or 'n' for no.")
    
    async def verify_plugin_connection(self) -> bool:
        """Verify that the plugin has connected to all sessions"""
        if not self.session_data_list:
            return False
        
        print("Waiting for plugin connection(s)...")
        
        # Wait up to 60 seconds for all connections
        for attempt in range(12):  # 12 attempts * 5 seconds = 60 seconds
            all_connected = True
            
            for i, session_data in enumerate(self.session_data_list):
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            f"{self.server_url}/sessions/{session_data['session_id']}/status"
                        ) as response:
                            if response.status == 200:
                                status_data = await response.json()
                                if status_data.get('status') == 'active' and status_data.get('instance_id'):
                                    print(f"✅ Session {i+1} connected (instance: {status_data['instance_id']})")
                                else:
                                    print(f"⏳ Session {i+1} waiting for connection...")
                                    all_connected = False
                            else:
                                print(f"❌ Could not verify connection for session {i+1}")
                                all_connected = False
                except Exception as e:
                    print(f"⚠️  Error checking session {i+1}: {e}")
                    all_connected = False
            
            if all_connected:
                print("✅ All plugin connections verified")
                return True
            
            if attempt < 11:  # Don't wait after the last attempt
                await asyncio.sleep(5)  # Wait 5 seconds between attempts
        
        print("❌ Plugin connection(s) not detected after 60 seconds")
        return False
    
    async def get_active_sessions_for_user(self) -> List[Dict[str, Any]]:
        """Get all active sessions for the test user"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.server_url}/sessions/{self.test_user_id}") as response:
                    if response.status == 200:
                        data = await response.json()
                        valid_sessions = data.get('valid_sessions', [])
                        # Filter for active sessions with instance_id (connected sessions)
                        connected_sessions = [
                            s for s in valid_sessions 
                            if s.get('status') == 'active' and s.get('instance_id')
                        ]
                        return connected_sessions
                    else:
                        print(f"❌ Failed to get user sessions (status {response.status})")
                        return []
        except Exception as e:
            print(f"❌ Error getting user sessions: {e}")
            return []
    
    async def run_standalone(self):
        """Run as standalone session tester"""
        print("="*70)
        print("🚀 RHINO MCP REMOTE - STANDALONE SESSION TESTER")
        print("="*70)
        print(f"Server URL: {self.server_url}")
        print()
        
        try:
            # Get license ID from user
            license_id = input("Enter your license ID (from registration): ").strip()
            if not license_id:
                print("❌ License ID is required")
                return False
                
            # Set up license data
            self.license_data = {"license_id": license_id}
            
            # Create session
            success = await self.create_host_session()
            if not success:
                return False
            
            # Guide user through connection
            connected = self.prompt_user_plugin_connection()
            if not connected:
                return False
            
            # Verify connection
            verified = await self.verify_plugin_connection()
            if verified:
                print("\n🎉 SUCCESS! Session is active and connected!")
                print(f"\nWebSocket URL: {self.session_data['websocket_url']}")
                print("\nYou can now use the plugin in Rhino or connect MCP clients.")
                
                # Offer to monitor
                monitor = input("\nMonitor session status? (y/n): ").strip().lower()
                if monitor in ['y', 'yes']:
                    await self.monitor_session()
                return True
            else:
                print("\n⚠️ Connection verification failed")
                return False
                
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def monitor_session(self):
        """Monitor session status with live updates"""
        if not self.session_data:
            return
            
        print(f"\n📊 Monitoring session {self.session_data['session_id'][:12]}...")
        print("Press Ctrl+C to stop")
        print("-" * 50)
        
        try:
            import aiohttp
            from datetime import datetime
            
            while True:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            f"{self.server_url}/sessions/{self.session_data['session_id']}/status"
                        ) as response:
                            if response.status == 200:
                                status_data = await response.json()
                                timestamp = datetime.now().strftime("%H:%M:%S")
                                status = status_data.get('status', 'unknown')
                                instance = status_data.get('instance_id', 'none')
                                print(f"[{timestamp}] Status: {status}, Instance: {instance[:12]}..." if instance != 'none' else f"[{timestamp}] Status: {status}, Instance: {instance}")
                            else:
                                print(f"❌ Failed to get status (HTTP {response.status})")
                                break
                except Exception as e:
                    print(f"⚠️ Error checking status: {e}")
                
                await asyncio.sleep(10)  # Update every 10 seconds
                
        except KeyboardInterrupt:
            print("\n👋 Monitoring stopped")


def _main():
    """Run the session tester standalone"""
    tester = SessionTester()
    asyncio.run(tester.run_standalone())


if __name__ == "__main__":
    _main()