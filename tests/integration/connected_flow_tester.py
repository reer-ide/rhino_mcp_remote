"""
Main connected flow tester that combines all test modules
"""

import asyncio
from typing import Dict, Any, Optional, List
from .license_tester import LicenseTester
from .session_tester import SessionTester
from .mcp_tools_tester import MCPToolsTester
from .quick_tester import QuickTester


class ConnectedFlowTester(QuickTester, LicenseTester):
    """Complete integration tester for connected flow between server and Rhino plugin"""
    
    async def run_full_test(self) -> bool:
        """Run the complete integration test flow"""
        test_results = {
            'total': 0,
            'passed': 0,
            'failed': 0
        }
        
        # Step 1: Check server
        print("Step 1: Checking server status...")
        if not await self.check_server_running():
            print("\n❌ Server is not running. Please start the server first with:")
            print("   cd remote_server && python run_server.py")
            return False
        
        # Step 2: Clear previous test data (optional)
        print("\nStep 2: Clearing previous test data...")
        await self.clear_test_data()
        
        # Step 3: Generate license
        print("\nStep 3: Generating test license...")
        if not await self.generate_test_license():
            return False
        
        # Step 4: Guide user through license registration
        print("\nStep 4: License registration in Rhino plugin...")
        if not self.prompt_user_license_registration():
            return False
        
        # Optional: Verify license registration
        # await self.verify_license_registration()
        
        # Step 5: Create host session(s)
        print("\nStep 5: Creating host session(s)...")
        if not await self.create_host_session():
            return False
        
        # Step 6: Guide user through plugin connection
        print("\nStep 6: Plugin connection...")
        if not self.prompt_user_plugin_connection():
            return False
        
        # Step 7: Verify plugin connection
        print("\nStep 7: Verifying plugin connection...")
        if not await self.verify_plugin_connection():
            return False
        
        # Step 8: Test MCP tools
        print("\nStep 8: Testing MCP tools...")
        return await self.test_mcp_tools()
    
    async def run_connection_test_only(self) -> bool:
        """Test only the connection flow without MCP tools"""
        # Steps 1-7 of the full test
        print("🔌 Connection Test Only Mode")
        print("=" * 60)
        
        # Check server
        if not await self.check_server_running():
            return False
        
        # Clear data
        await self.clear_test_data()
        
        # Generate license
        if not await self.generate_test_license():
            return False
        
        # License registration
        if not self.prompt_user_license_registration():
            return False
        
        # Create session
        if not await self.create_host_session():
            return False
        
        # Plugin connection
        if not self.prompt_user_plugin_connection():
            return False
        
        # Verify connection
        if await self.verify_plugin_connection():
            print("\n✅ Connection test passed!")
            return True
        else:
            print("\n❌ Connection test failed!")
            return False