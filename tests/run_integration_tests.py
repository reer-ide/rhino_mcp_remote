#!/usr/bin/env python3
"""
Integration Test Runner for Remote MCP Server
Provides options for running in-memory tests, integration tests, or both.
"""

import asyncio
import sys
import os
import argparse
from datetime import datetime

# Add the parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def run_in_memory_tests():
    """Run in-memory tests using the existing test runner"""
    print("🧪 Running In-Memory Tests")
    print("=" * 50)
    
    try:
        # Import and run the existing test runner
        from test_mcp_runner import MCPTestRunner
        
        runner = MCPTestRunner()
        results = await runner.run_all_tests()
        
        return results["summary"]["failed"] == 0
    except Exception as e:
        print(f"❌ Error running in-memory tests: {e}")
        return False

async def run_integration_tests():
    """Run integration tests with actual server and Rhino connection"""
    print("🔗 Running Integration Tests")
    print("=" * 50)
    
    try:
        # Import and run the integration test
        from test_integration_connected_flow import ConnectedFlowTester
        
        tester = ConnectedFlowTester()
        success = await tester.run_complete_integration_test()
        
        return success
    except Exception as e:
        print(f"❌ Error running integration tests: {e}")
        return False

async def run_all_tests():
    """Run both in-memory and integration tests"""
    print("🚀 Running Complete Test Suite")
    print("=" * 80)
    print("This will run both in-memory and integration tests.")
    print()
    
    # Run in-memory tests first
    print("Phase 1: In-Memory Tests")
    print("-" * 30)
    in_memory_success = await run_in_memory_tests()
    
    print(f"\nPhase 1 Result: {'✅ PASSED' if in_memory_success else '❌ FAILED'}")
    
    if not in_memory_success:
        print("⚠️  In-memory tests failed. You may want to fix these before running integration tests.")
        proceed = input("Continue with integration tests anyway? (y/n): ").strip().lower()
        if proceed not in ['y', 'yes']:
            return False
    
    print("\n" + "="*80)
    print("Phase 2: Integration Tests")
    print("-" * 30)
    
    integration_success = await run_integration_tests()
    
    print(f"\nPhase 2 Result: {'✅ PASSED' if integration_success else '❌ FAILED'}")
    
    # Final summary
    print("\n" + "="*80)
    print("📊 COMPLETE TEST SUITE RESULTS")
    print("="*80)
    print(f"In-Memory Tests: {'✅ PASSED' if in_memory_success else '❌ FAILED'}")
    print(f"Integration Tests: {'✅ PASSED' if integration_success else '❌ FAILED'}")
    
    overall_success = in_memory_success and integration_success
    print(f"\nOverall Result: {'🎉 ALL TESTS PASSED' if overall_success else '⚠️  SOME TESTS FAILED'}")
    
    return overall_success

def main():
    """Main entry point with command line options"""
    parser = argparse.ArgumentParser(
        description="Remote MCP Server Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Test Types:
  in-memory     - Fast tests using FastMCP in-memory client (no external deps)
  integration   - Full flow tests with actual server and Rhino connection
  all          - Run both in-memory and integration tests sequentially

Examples:
  python run_integration_tests.py                    # Interactive mode
  python run_integration_tests.py in-memory          # Only in-memory tests
  python run_integration_tests.py integration        # Only integration tests  
  python run_integration_tests.py all                # Run all tests
        """
    )
    
    parser.add_argument(
        'test_type',
        nargs='?',
        choices=['in-memory', 'integration', 'all'],
        help='Type of tests to run'
    )
    
    parser.add_argument(
        '--skip-prompt',
        action='store_true',
        help='Skip interactive prompts (for automated testing)'
    )
    
    args = parser.parse_args()
    
    # Print header
    print("🧪 Remote MCP Server Test Runner")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Determine test type
    test_type = args.test_type
    
    if not test_type and not args.skip_prompt:
        print("Available test types:")
        print("1. in-memory    - Fast tests (no external dependencies)")
        print("2. integration  - Full flow tests (requires server + Rhino)")
        print("3. all         - Run both test types")
        print()
        
        while True:
            choice = input("Select test type (1-3): ").strip()
            if choice == '1':
                test_type = 'in-memory'
                break
            elif choice == '2':
                test_type = 'integration'
                break
            elif choice == '3':
                test_type = 'all'
                break
            else:
                print("Please enter 1, 2, or 3.")
    
    # Default to in-memory if no choice made
    if not test_type:
        test_type = 'in-memory'
        print("Defaulting to in-memory tests...")
    
    print(f"Running: {test_type} tests")
    print()
    
    # Run the appropriate tests
    async def run_tests():
        if test_type == 'in-memory':
            return await run_in_memory_tests()
        elif test_type == 'integration':
            return await run_integration_tests()
        elif test_type == 'all':
            return await run_all_tests()
        else:
            print(f"❌ Unknown test type: {test_type}")
            return False
    
    # Execute tests
    try:
        success = asyncio.run(run_tests())
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n❌ Tests cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 