#!/usr/bin/env python3
"""
Integration Tests for Connected Flow - Remote MCP Server + Rhino Plugin
Tests the complete flow with the new connect-only architecture:
1. Host application creates sessions via /sessions/create
2. Plugin connects to existing sessions via /sessions/connect  
3. MCP tools are tested through the established connection
"""

import asyncio
import sys
import json
from integration import ConnectedFlowTester


async def main():
    """Main test runner"""
    # Check command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command in ['quick', 'tools', 'q', 't']:
            # Quick test mode
            print("[TEST] Quick MCP Tool Test")
            print("=" * 50)
            print("Testing MCP tools with existing connected sessions...")
            print()
            
            tester = ConnectedFlowTester()
            success = await tester.quick_test_tools()
            
        elif command in ['connection', 'connect', 'c']:
            # Connection test only
            print("[TEST] Connection Test Mode")
            print("=" * 50)
            print("Testing connection flow without MCP tools...")
            print()
            
            tester = ConnectedFlowTester()
            success = await tester.run_connection_test_only()
            
        elif command == 'help':
            # Show help
            print("Remote MCP Integration Test")
            print("=" * 50)
            print("\nUsage:")
            print("  python test_integration_connected_flow.py [command]")
            print("\nCommands:")
            print("  (no command)     Run full integration test")
            print("  quick, q         Quick test using existing connected sessions")
            print("  connection, c    Test connection flow only (no MCP tools)")
            print("  help            Show this help message")
            print("\nExamples:")
            print("  python test_integration_connected_flow.py")
            print("  python test_integration_connected_flow.py quick")
            print("  python test_integration_connected_flow.py connection")
            return
            
        else:
            print(f"Unknown command: {command}")
            print("Use 'help' to see available commands")
            return
            
    else:
        # Full test mode
        print("[TEST] Remote MCP Server + Rhino Plugin Integration Test")
        print("=" * 80)
        print()
        
        # Check if user wants to proceed
        print("This test verifies the new connect-only architecture:")
        print("1. Host application creates sessions (simulated by test)")
        print("2. Plugin connects to existing sessions")
        print("3. MCP tools are tested through the connection")
        print()
        print("Requirements:")
        print("- Remote MCP server running (python run_server.py)")
        print("- Rhino with RhinoMCP plugin loaded")
        print("- Test .3dm file(s)")
        print()
        
        proceed = input("Continue with full integration test? (y/n): ").strip().lower()
        if proceed not in ['y', 'yes']:
            print("Test cancelled.")
            return
        
        print()
        tester = ConnectedFlowTester()
        success = await tester.run_full_test()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())