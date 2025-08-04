"""
Quick test functionality for testing with existing connected sessions
"""

import asyncio
import json
from typing import Dict, Any, Optional, List
from .session_tester import SessionTester
from .mcp_tools_tester import MCPToolsTester


class QuickTester(SessionTester, MCPToolsTester):
    """Quick test functionality that uses existing connected sessions"""
    
    async def quick_test_tools(self) -> bool:
        """Quick test - find connected sessions and run tool tests directly"""
        print("[TEST] Quick MCP Tool Test (using existing connected sessions)")
        print("=" * 60)
        
        # Step 1: Check server
        print("Step 1: Checking server status...")
        if not await self.check_server_running():
            print("\n[ERROR] Server is not running. Please start the server first.")
            return False
        
        # Step 2: Look for connected sessions (sessions with instance_id)
        print("\nStep 2: Looking for connected sessions...")
        connected_sessions = await self.get_active_sessions_for_user()
        
        if not connected_sessions:
            print("[ERROR] No connected sessions found.")
            print("\nTo use quick test, you need:")
            print("1. An active session created by the host app")
            print("2. Rhino plugin connected to that session")
            print("\nAlternatively, run the full test to set up everything.")
            return False
        
        print(f"[SUCCESS] Found {len(connected_sessions)} connected session(s)")
        
        # Display session info and let user choose
        if len(connected_sessions) == 1:
            # Single session - use it directly
            session = connected_sessions[0]
            print(f"\nUsing session: {session['session_id']}")
            print(f"File: {session['file_path']}")
            print(f"Status: {session['status']}")
            print(f"Instance: {session['instance_id']}")
            
            self.session_data_list = [session]
            self.session_data = session
            
            # Set license data from session
            self.license_data = {
                'license_id': session.get('license_id'),
                'issued_to': self.test_user_id
            }
        else:
            # Multiple sessions - let user choose
            print("\nMultiple connected sessions found:")
            for i, session in enumerate(connected_sessions):
                print(f"\n{i+1}. Session: {session['session_id'][:8]}...")
                print(f"   File: {session['file_path']}")
                print(f"   Instance: {session['instance_id']}")
            
            while True:
                choice = input("\nSelect session(s) to test (1-n for single, 'all' for all): ").strip().lower()
                
                if choice == 'all':
                    self.session_data_list = connected_sessions
                    self.session_data = connected_sessions[0]
                    print(f"[INFO] Testing all {len(connected_sessions)} sessions")
                    break
                elif choice.isdigit():
                    idx = int(choice) - 1
                    if 0 <= idx < len(connected_sessions):
                        self.session_data_list = [connected_sessions[idx]]
                        self.session_data = connected_sessions[idx]
                        print(f"[INFO] Selected session {idx + 1}")
                        break
                    else:
                        print("[ERROR] Invalid selection. Please try again.")
                else:
                    print("[ERROR] Invalid input. Enter a number or 'all'.")
            
            # Set license data from first session
            self.license_data = {
                'license_id': self.session_data_list[0].get('license_id'),
                'issued_to': self.test_user_id
            }
        
        # Step 3: Confirm with user
        print("\n" + "="*60)
        print("[INFO] Ready to test MCP tools")
        print("="*60)
        print(f"Sessions to test: {len(self.session_data_list)}")
        print("\nThis will test:")
        print("  • Scene information retrieval")
        print("  • Object creation")
        print("  • Object selection")
        print("  • Metadata management")
        print("  • Layer management")
        print()
        
        try:
            confirm = input("Continue with testing? (y/n): ").strip().lower()
            if confirm not in ['y', 'yes']:
                print("[INFO] Test cancelled by user")
                return False
        except EOFError:
            # Non-interactive mode, proceed automatically
            print("Continue with testing? (y/n): y [auto]")
            print("[INFO] Running in non-interactive mode, proceeding automatically")
        
        # Step 4: Run MCP tool tests
        print("\nStep 3: Testing MCP tools...")
        return await self.test_mcp_tools()
    
    async def quick_test_specific_tool(self, tool_name: str, arguments: Dict[str, Any]) -> bool:
        """Quick test a specific tool with custom arguments"""
        print(f"🔧 Quick Test: {tool_name}")
        print("=" * 60)
        
        # Check server and get sessions
        if not await self.check_server_running():
            print("[ERROR] Server is not running")
            return False
        
        connected_sessions = await self.get_active_sessions_for_user()
        if not connected_sessions:
            print("[ERROR] No connected sessions found")
            return False
        
        # Use first connected session
        session = connected_sessions[0]
        print(f"Using session: {session['session_id'][:8]}...")
        print(f"File: {session['file_path']}")
        
        # Set up context
        context = {
            'license_id': session.get('license_id'),
            'user_id': self.test_user_id,
            'session_id': session['session_id']
        }
        
        # Call the tool
        try:
            print(f"\nCalling {tool_name} with arguments:")
            print(json.dumps(arguments, indent=2))
            
            result = await self.mcp_client.call_tool(tool_name, arguments=arguments, context=context)
            
            print("\nResult:")
            print(json.dumps(result, indent=2))
            
            return result.get('type') == 'response'
        except Exception as e:
            print(f"[ERROR] Error calling tool: {e}")
            return False