"""
Quick test functionality for testing with existing connected sessions
"""

import asyncio
import json
from typing import Dict, Any, Optional, List
from .session_tester import SessionTester


class QuickTester(SessionTester):
    """Quick test functionality that uses existing connected sessions"""
    
    async def quick_test_tools(self) -> bool:
        """Quick test - find connected sessions and verify they are active"""
        print("[TEST] Quick Session Test (using existing connected sessions)")
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
        
        # Step 3: Verification complete
        print("\n" + "="*60)
        print("[INFO] Connected sessions verified")
        print("="*60)
        print(f"Sessions verified: {len(self.session_data_list)}")
        print()
        print("✅ Quick test completed successfully!")
        print("   All sessions are connected and ready for use.")
        print()

        return True