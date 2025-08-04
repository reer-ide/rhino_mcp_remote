"""
Base class for integration testing with common functionality
"""

import asyncio
import aiohttp
from typing import Dict, Any, Optional, List
from datetime import datetime
import os
import sys

# Add the parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class BaseIntegrationTester:
    """Base class for integration testing with common functionality"""
    
    def __init__(self, server_url: str = "http://127.0.0.1:8080"):
        self.server_url = server_url
        self.test_user_id = "integration-test-user"
        self.license_data: Optional[Dict[str, Any]] = None
        self.session_data: Optional[Dict[str, Any]] = None
        self.session_data_list: List[Dict[str, Any]] = []
        self.test_files: List[str] = []
        self.test_results: List[Dict[str, Any]] = []
        
    async def check_server_running(self) -> bool:
        """Check if the remote server is running"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.server_url}/health", timeout=5) as response:
                    if response.status == 200:
                        health_data = await response.json()
                        print(f"[SUCCESS] Server is running: {health_data.get('server', 'unknown')}")
                        print(f"   Architecture: {health_data.get('architecture', 'unknown')}")
                        return True
                    else:
                        print(f"[ERROR] Server responded with status {response.status}")
                        return False
        except Exception as e:
            print(f"[ERROR] Cannot connect to server: {e}")
            return False
    
    async def clear_test_data(self) -> bool:
        """Clear previous test data from mock Redis"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.server_url}/debug/mock-redis/clear") as response:
                    if response.status == 200:
                        clear_data = await response.json()
                        print("[SUCCESS] Previous test data cleared")
                        return True
                    else:
                        print(f"[WARNING] Could not clear test data (status {response.status})")
                        return False
        except Exception as e:
            print(f"[WARNING] Could not clear test data: {e}")
            return False
    
    def print_test_summary(self, test_results: Dict[str, int]) -> bool:
        """Print test summary and return success status"""
        print("\n" + "="*60)
        print("📊 Test Summary")
        print("="*60)
        print(f"Total tests: {test_results['total']}")
        print(f"Passed: {test_results['passed']} [PASS]")
        print(f"Failed: {test_results['failed']} [FAIL]")
        
        # Show individual test results
        if self.test_results:
            print("\nDetailed Results:")
            for result in self.test_results:
                status_icon = "[PASS]" if result['success'] else "[FAIL]"
                print(f"  {status_icon} {result['test_name']}: {result['message']}")
        
        # Final result
        success = test_results['failed'] == 0
        if success:
            print("\n🎉 All integration tests passed!")
        else:
            print(f"\n[WARNING] {test_results['failed']} tests failed. See details above.")
        
        return success
    
    async def get_test_file_path(self, prompt: str, default_path: str = None) -> str:
        """Helper method to get test file path from user"""
        print("Examples:")
        print("  • C:/path/to/your/test.3dm")
        print("  • /Users/yourname/Documents/test_file.3dm")
        if default_path:
            print(f"  • Default: {default_path}")
        print()
        
        while True:
            if default_path:
                user_input = input(f"{prompt} (press Enter for default): ").strip()
                current_file = user_input if user_input else default_path
            else:
                current_file = input(prompt).strip()
            
            if not current_file:
                print("[ERROR] Please enter a file path or press Enter for default.")
                continue
            
            # Convert to forward slashes for consistency
            current_file = current_file.replace("\\", "/")
            
            # Basic validation
            if not current_file.endswith('.3dm'):
                print("[WARNING] File should have .3dm extension. Continue anyway? (y/n): ", end="")
                if input().strip().lower() not in ['y', 'yes']:
                    continue
            
            print(f"[SUCCESS] Using test file: {current_file}")
            return current_file
    
    def add_test_result(self, test_name: str, success: bool, message: str):
        """Add a test result to the results list"""
        self.test_results.append({
            'test_name': test_name,
            'success': success,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })