"""
License management functionality for integration tests
"""

import asyncio
import aiohttp
from typing import Dict, Any, Optional
from .base_tester import BaseIntegrationTester


class LicenseTester(BaseIntegrationTester):
    """Handles license generation and verification for tests"""
    
    async def generate_test_license(self) -> bool:
        """Generate a license for the test user"""
        try:
            license_request = {
                "issued_to": self.test_user_id,
                "tier": "beta",
                "max_concurrent_files": 3,
                "validity_days": 30
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.server_url}/license/generate", 
                    json=license_request
                ) as response:
                    if response.status == 200:
                        self.license_data = await response.json()
                        print("✅ License generated successfully")
                        print(f"   License ID: {self.license_data['license_id']}")
                        print(f"   License Key: {self.license_data['license_key']}")
                        print(f"   Issued To: {self.license_data['issued_to']}")
                        print(f"   Tier: {self.license_data['tier']}")
                        print(f"   Max Files: {self.license_data['max_concurrent_files']}")
                        return True
                    else:
                        error_data = await response.json()
                        print(f"❌ License generation failed: {error_data.get('error', 'Unknown error')}")
                        return False
        except Exception as e:
            print(f"❌ Error generating license: {e}")
            return False
    
    def prompt_user_license_registration(self) -> bool:
        """Guide user through license registration in Rhino plugin"""
        if not self.license_data:
            print("❌ No license data available for registration")
            return False
        
        print("\n" + "="*80)
        print("📋 USER ACTION REQUIRED: License Registration")
        print("="*80)
        print()
        print("Please perform the following steps in Rhino:")
        print()
        print("1. Make sure the RhinoMCP plugin is loaded in Rhino")
        print("2. Run the following command in Rhino command line:")
        print()
        print(f"   ReerLicense --> Register")
        print()
        print("3. When prompted, enter the following license key:")
        print(f"   {self.license_data['license_key']}")
        print()
        print("4. When prompted, enter the user ID:")
        print(f"   {self.test_user_id}")
        print()
        print("5. The plugin should register and store the license locally")
        print()
        
        while True:
            user_input = input("✅ License registration completed? (y/n): ").strip().lower()
            if user_input in ['y', 'yes']:
                return True
            elif user_input in ['n', 'no']:
                print("❌ License registration not completed. Please try again.")
                return False
            else:
                print("Please enter 'y' for yes or 'n' for no.")
    
    async def verify_license_registration(self) -> bool:
        """Verify that the license was registered successfully"""
        if not self.license_data:
            return False
        
        print("Waiting for license registration to complete...")
        
        # Wait up to 60 seconds for license registration
        for attempt in range(12):  # 12 attempts * 5 seconds = 60 seconds
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{self.server_url}/license/{self.license_data['license_id']}/info"
                    ) as response:
                        if response.status == 200:
                            license_info = await response.json()
                            if license_info.get('status') == 'active':
                                print("✅ License registration verified")
                                return True
                            else:
                                print(f"⚠️  License status: {license_info.get('status', 'unknown')}")
                        elif response.status == 404:
                            print(f"⏳ License not yet registered (attempt {attempt + 1}/12)")
                        else:
                            print(f"❌ Could not verify license registration (status {response.status})")
            except Exception as e:
                print(f"⚠️  Error checking license registration: {e}")
            
            if attempt < 11:  # Don't wait after the last attempt
                await asyncio.sleep(5)  # Wait 5 seconds between attempts
        
        print("❌ License registration not detected after 60 seconds")
        return False