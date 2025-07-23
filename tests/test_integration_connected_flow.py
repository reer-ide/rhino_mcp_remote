#!/usr/bin/env python3
"""
Integration Tests for Connected Flow - Remote MCP Server + Rhino Plugin
Tests the complete flow with actual server and plugin connection.
"""

import asyncio
import aiohttp
import json
import time
import uuid
import base64
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import sys
import os
from fastmcp import FastMCP, Client
from fastmcp.client import StreamableHttpTransport

# Add the parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class ConnectedFlowTester:
    """Integration tester for connected flow between server and Rhino plugin"""
    
    def __init__(self, server_url: str = "http://127.0.0.1:8080"):
        self.server_url = server_url
        self.test_user_id = "integration-test-user"
        self.license_data: Optional[Dict[str, Any]] = None
        self.session_data: Optional[Dict[str, Any]] = None
        self.test_results: List[Dict[str, Any]] = []
        self.mcp_client = Client(StreamableHttpTransport(self.server_url+"/mcp"))
        
    async def check_server_running(self) -> bool:
        """Check if the remote server is running"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.server_url}/health", timeout=5) as response:
                    if response.status == 200:
                        health_data = await response.json()
                        print(f"✅ Server is running: {health_data.get('server', 'unknown')}")
                        print(f"   Architecture: {health_data.get('architecture', 'unknown')}")
                        return True
                    else:
                        print(f"❌ Server responded with status {response.status}")
                        return False
        except Exception as e:
            print(f"❌ Cannot connect to server: {e}")
            return False
    
    async def clear_test_data(self) -> bool:
        """Clear previous test data from mock Redis"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.server_url}/debug/mock-redis/clear") as response:
                    if response.status == 200:
                        clear_data = await response.json()
                        print("✅ Previous test data cleared")
                        return True
                    else:
                        print(f"⚠️  Could not clear test data (status {response.status})")
                        return False
        except Exception as e:
            print(f"⚠️  Could not clear test data: {e}")
            return False
    
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
        print("3. When prompted, enter the server URL:")
        print(f"   {self.server_url}")
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
    
    def prompt_user_connection_setup(self) -> bool:
        """Guide user through connection setup in Rhino"""
        print("\n" + "="*80)
        print("🔗 USER ACTION REQUIRED: Connection Setup")
        print("="*80)
        print()
        print("Please perform the following steps in Rhino:")
        print()
        print("1. Open a Rhino file (.3dm) or create a new document")
        print("2. Run the following command in Rhino command line:")
        print()
        print("   ReerStart")
        print()
        print("3. When prompted for connection type, choose 'remote'")
        print("4. When prompted for server URL, enter:")
        print(f"   {self.server_url}")
        print("5. The plugin should connect to the remote server and establish a session")
        print("6. You should see success messages in Rhino indicating the connection is established")
        print()
        print("Expected output in Rhino:")
        print("  - 'Session created successfully'")
        print("  - 'WebSocket connection established'")
        print("  - Session details with session ID")
        print()
        
        while True:
            user_input = input("✅ Connection established? (y/n): ").strip().lower()
            if user_input in ['y', 'yes']:
                return True
            elif user_input in ['n', 'no']:
                print("❌ Connection not established. Please try again.")
                print("💡 Common issues:")
                print("   - Make sure the server is still running")
                print("   - Check that you selected 'remote' connection type")
                print("   - Verify the server URL was entered correctly")
                print("   - Check Rhino command history for error messages")
                return False
            else:
                print("Please enter 'y' for yes or 'n' for no.")
    
    async def find_active_session(self) -> bool:
        """Find the active session created by the plugin connection"""
        print("Waiting for session to be established...")
        
        # Wait up to 90 seconds for session creation
        for attempt in range(18):  # 18 attempts * 5 seconds = 90 seconds
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{self.server_url}/debug/mock-redis") as response:
                        if response.status == 200:
                            redis_data = await response.json()
                            
                            # Look for sessions in connection manager data
                            conn_data = redis_data.get('connection_manager', {}).get('data_summary', {})
                            sessions = conn_data.get('sessions', {})
                            
                            if sessions:
                                # Find session for our test user
                                for session_id, session_info in sessions.items():
                                    if session_info.get('user_id') == self.test_user_id:
                                        self.session_data = {
                                            'session_id': session_id,
                                            **session_info
                                        }
                                        print(f"✅ Found session: {session_id}")
                                        print(f"   User ID: {session_info.get('user_id')}")
                                        print(f"   Status: {session_info.get('status')}")
                                        print(f"   File Path: {session_info.get('file_path')}")
                                        print(f"   License ID: {session_info.get('license_id')}")
                                        return True
                            
                            if attempt == 0 or attempt % 6 == 0:  # Print every 30 seconds
                                print(f"⏳ No session found yet (attempt {attempt + 1}/18)")
                                print(f"   Available sessions: {list(sessions.keys()) if sessions else 'None'}")
                        else:
                            print(f"❌ Could not query session data (status {response.status})")
            except Exception as e:
                print(f"⚠️  Error checking for session: {e}")
            
            if attempt < 17:  # Don't wait after the last attempt
                await asyncio.sleep(5)  # Wait 5 seconds between attempts
        
        print("❌ No active session found after 90 seconds")
        print("This usually means the ReerStart connection failed or didn't create a session")
        return False
    
    async def test_mcp_tool_call(self, tool_name: str, parameters: Dict[str, Any], 
                                expected_fields: List[str] = None) -> Dict[str, Any]:
        """Test a single MCP tool call and validate response"""
        if not self.session_data:
            return {
                "tool": tool_name,
                "status": "FAIL",
                "error": "No active session available"
            }
        
        try:
            # Add session_id to parameters
            print(f"Adding {self.session_data['session_id']} to params")
            tool_params = {
                "session_id": self.session_data['session_id'],
                **parameters
            }
            
            start_time = time.time()
            
            # Use async context manager as required by FastMCP
            async with self.mcp_client:
                response = await self.mcp_client.call_tool(tool_name, tool_params)
                    
            duration = time.time() - start_time
                    
            # Handle different response formats from FastMCP
            response_data = None
            
            if hasattr(response, 'status') and response.status == 200:
                response_data = await response.json()
                
                # Extract the actual tool response
                if 'result' in response_data and 'content' in response_data['result']:
                    content = response_data['result']['content']
                    if content and len(content) > 0:
                        tool_response_text = content[0]['text']
                        try:
                            tool_response = json.loads(tool_response_text)
                        except json.JSONDecodeError:
                            # If it's not JSON, treat as plain text response
                            tool_response = tool_response_text
                        
                        # Validate expected fields if provided (only for dict responses)
                        validation_errors = []
                        if expected_fields and isinstance(tool_response, dict):
                            for field in expected_fields:
                                if field not in tool_response:
                                    validation_errors.append(f"Missing field: {field}")
                        
                        if validation_errors:
                            return {
                                "tool": tool_name,
                                "status": "FAIL",
                                "error": f"Validation failed: {', '.join(validation_errors)}",
                                "response": tool_response,
                                "duration_ms": round(duration * 1000, 2)
                            }
                        else:
                            return {
                                "tool": tool_name,
                                "status": "PASS",
                                "response": tool_response,
                                "duration_ms": round(duration * 1000, 2)
                            }
                    else:
                        return {
                            "tool": tool_name,
                            "status": "FAIL",
                            "error": "Empty content in response",
                            "duration_ms": round(duration * 1000, 2)
                        }
                else:
                    return {
                        "tool": tool_name,
                        "status": "FAIL",
                        "error": "Invalid MCP response format",
                        "response": response_data,
                        "duration_ms": round(duration * 1000, 2)
                    }
            elif hasattr(response, 'data'):
                # Handle direct response case
                tool_response = response.data
                
                # Try to parse as JSON if it's a string
                if isinstance(tool_response, str):
                    try:
                        tool_response = json.loads(tool_response)
                    except json.JSONDecodeError:
                        pass  # Keep as string
                
                return {
                    "tool": tool_name,
                    "status": "PASS",
                    "response": tool_response,
                    "duration_ms": round(duration * 1000, 2)
                }
            elif hasattr(response, '__class__') and 'Image' in str(response.__class__):
                # Handle FastMCP Image response type
                return {
                    "tool": tool_name,
                    "status": "PASS", 
                    "response": {"type": "image", "class": str(response.__class__)},
                    "duration_ms": round(duration * 1000, 2)
                }
            elif str(response.__class__).endswith('Image'):
                # Additional check for Image class (in case class name doesn't contain "Image")
                return {
                    "tool": tool_name,
                    "status": "PASS",
                    "response": {"type": "image", "image_object": True},
                    "duration_ms": round(duration * 1000, 2)
                }
            elif hasattr(response, '__class__') and 'ToolResult' in str(response.__class__):
                # Handle ToolResult response type
                return {
                    "tool": tool_name,
                    "status": "PASS",
                    "response": {"type": "tool_result", "class": str(response.__class__)},
                    "duration_ms": round(duration * 1000, 2)
                }
            else:
                error_text = str(response) if response else "No response"
                return {
                    "tool": tool_name,
                    "status": "FAIL",
                    "error": f"Unexpected response format: {error_text}",
                    "duration_ms": round(duration * 1000, 2)
                }
                    
        except Exception as e:
            return {
                "tool": tool_name,
                "status": "FAIL",
                "error": f"Exception: {str(e)}"
            }
    
    async def run_mcp_tool_tests(self) -> Dict[str, Any]:
        """Run comprehensive MCP tool tests following a logical workflow"""
        print("\n" + "="*80)
        print("🧪 Running Comprehensive MCP Tool Tests")
        print("="*80)
        print("Following logical workflow: Scene Info → Layer → Objects → Metadata → Modify → Script → Cleanup")
        
        results = {"passed": 0, "failed": 0, "tests": []}
        
        # Shared test data
        test_layer_name = "IntegrationTest_Layer"
        created_object_ids = []
        created_layer_ids = []
        document_units = "Unknown"
        unit_scale_factor = 1.0  # Default scale factor
        
        # Phase 1: Initial Scene State
        print(f"\n📋 PHASE 1: Initial Scene Assessment")
        
        test_1 = await self.test_mcp_tool_call(
            "get_rhino_scene_info",
            {},
            ["document_name", "total_objects", "total_layers", "layers"]
        )
        results['tests'].append(test_1)
        if test_1['status'] == 'PASS':
            results['passed'] += 1
            print(f"   ✅ Initial scene info retrieved ({test_1.get('duration_ms', 0)}ms)")
            
            # Extract units and calculate scale factor for object dimensions
            if 'response' in test_1:
                response_data = test_1['response']
                if isinstance(response_data, str):
                    try:
                        response_data = json.loads(response_data)
                    except json.JSONDecodeError:
                        response_data = {}
                
                if 'document' in response_data and 'units' in response_data['document']:
                    document_units = response_data['document']['units']
                    print(f"   📏 Document units: {document_units}")
                    
                    # Scale factor based on units (assuming small objects need scaling up)
                    if document_units.lower() == 'millimeters':
                        unit_scale_factor = 100.0  # Scale up by 100 for visibility
                        print(f"   📐 Scaling objects by {unit_scale_factor}x for millimeter units")
                    elif document_units.lower() == 'meters':
                        unit_scale_factor = 0.1  # Scale down for meter units
                        print(f"   📐 Scaling objects by {unit_scale_factor}x for meter units")
                    elif document_units.lower() in ['inches', 'feet']:
                        unit_scale_factor = 10.0  # Moderate scale for imperial
                        print(f"   📐 Scaling objects by {unit_scale_factor}x for imperial units")
                    else:
                        print(f"   📐 Using default scale (1.0x) for units: {document_units}")
        else:
            results['failed'] += 1
            print(f"   ❌ Failed to get scene info: {test_1.get('error', 'Unknown')}")
        
        # Phase 2: Create Testing Layer
        print(f"\n🏗️  PHASE 2: Testing Infrastructure Setup")
        
        test_2 = await self.test_mcp_tool_call(
            "create_rhino_layers",
            {
                "layers": [
                    {
                        "name": test_layer_name,
                        "color": [255, 100, 50],
                        "is_visible": True,
                        "description": "Integration test layer"
                    }
                ]
            },
            ["status", "layers_created"]
        )
        results['tests'].append(test_2)
        if test_2['status'] == 'PASS':
            results['passed'] += 1
            print(f"   ✅ Testing layer created ({test_2.get('duration_ms', 0)}ms)")
            # Extract layer IDs for cleanup
            if 'response' in test_2:
                response_data = test_2['response']
                if isinstance(response_data, str):
                    try:
                        response_data = json.loads(response_data)
                    except json.JSONDecodeError:
                        response_data = {}
                layers_created = response_data.get('layers_created', [])
                for layer in layers_created:
                    if 'id' in layer:
                        created_layer_ids.append(layer['id'])
        else:
            results['failed'] += 1
            print(f"   ❌ Failed to create layer: {test_2.get('error', 'Unknown')}")
        
        # Phase 3: Create Test Objects
        print(f"\n📦 PHASE 3: Object Creation")
        
        test_3 = await self.test_mcp_tool_call(
            "create_rhino_basic_objects",
            {
                "objects": [
                    {
                        "type": "BOX",
                        "name": "TestBox_1",
                        "layer": test_layer_name,
                        "params": {
                            "center": [0, 0, 0],
                            "width": 5 * unit_scale_factor,
                            "length": 3 * unit_scale_factor,
                            "height": 2 * unit_scale_factor
                        }
                    },
                    {
                        "type": "SPHERE",
                        "name": "TestSphere_1", 
                        "layer": test_layer_name,
                        "params": {
                            "center": [10 * unit_scale_factor, 0, 0],
                            "radius": 2 * unit_scale_factor
                        }
                    },
                    {
                        "type": "CYLINDER",
                        "name": "TestCylinder_1",
                        "layer": test_layer_name,
                        "params": {
                            "center": [20 * unit_scale_factor, 0, 0],
                            "radius": 1.5 * unit_scale_factor,
                            "height": 4 * unit_scale_factor
                        }
                    }
                ]
            },
            ["status", "objects_created", "count"]
        )
        results['tests'].append(test_3)
        if test_3['status'] == 'PASS':
            results['passed'] += 1
            print(f"   ✅ Test objects created ({test_3.get('duration_ms', 0)}ms)")
            # Extract object IDs for later tests
            if 'response' in test_3:
                response_data = test_3['response']
                if isinstance(response_data, str):
                    try:
                        response_data = json.loads(response_data)
                    except json.JSONDecodeError:
                        response_data = {}
                objects_created = response_data.get('objects_created', [])
                for obj in objects_created:
                    # Try both 'id' and 'object_id' fields
                    obj_id = obj.get('id') or obj.get('object_id')
                    if obj_id:
                        created_object_ids.append(obj_id)
                        print(f"   📝 Captured object ID: {obj_id}")
                
                # Debug: print response structure if no objects found
                if not created_object_ids:
                    print(f"   ⚠️  No object IDs found in response. Response structure: {response_data}")
                    # Try alternative response formats
                    if 'results' in response_data:
                        for obj in response_data['results'].values() if isinstance(response_data['results'], dict) else response_data['results']:
                            obj_id = obj.get('id') or obj.get('object_id')
                            if obj_id:
                                created_object_ids.append(obj_id)
                                print(f"   📝 Found object ID in results: {obj_id}")
                
                print(f"   📊 Total object IDs captured: {len(created_object_ids)}")
        else:
            results['failed'] += 1
            print(f"   ❌ Failed to create objects: {test_3.get('error', 'Unknown')}")
        
        # Phase 4: Add Metadata to Objects
        print(f"\n🏷️  PHASE 4: Metadata Management")
        
        if created_object_ids:
            test_4 = await self.test_mcp_tool_call(
                "add_rhino_objects_metadata",
                {
                    "object_ids": [created_object_ids[0]],
                    "name": "TestObject_Updated",
                    "description": "Integration test geometry with metadata"
                },
                ["status", "objects_processed"]
            )
            results['tests'].append(test_4)
            if test_4['status'] == 'PASS':
                results['passed'] += 1
                print(f"   ✅ Metadata added to objects ({test_4.get('duration_ms', 0)}ms)")
            else:
                results['failed'] += 1
                print(f"   ❌ Failed to add metadata: {test_4.get('error', 'Unknown')}")
        else:
            print("   ⚠️  No object IDs available, skipping metadata test...")
            # Note: add_rhino_objects_metadata requires object IDs, not names
        
        # Phase 5: Update Metadata
        if created_object_ids:
            test_5 = await self.test_mcp_tool_call(
                "update_rhino_objects_metadata",
                {
                    "object_ids": [created_object_ids[0]],
                    "name": "TestObject_Final",
                    "description": "Updated during integration testing"
                },
                ["status", "objects_processed"]
            )
            results['tests'].append(test_5)
            if test_5['status'] == 'PASS':
                results['passed'] += 1
                print(f"   ✅ Metadata updated ({test_5.get('duration_ms', 0)}ms)")
            else:
                results['failed'] += 1
                print(f"   ❌ Failed to update metadata: {test_5.get('error', 'Unknown')}")
        else:
            print("   ⚠️  No object IDs available, skipping update metadata test...")
            # Note: update_rhino_objects_metadata requires object IDs, not names
        
        # Phase 6: Get Objects Info
        print(f"\n📊 PHASE 5: Information Retrieval")
        
        test_6 = await self.test_mcp_tool_call(
            "get_rhino_objects_info",
            {"get_all_objects": True, "include_attributes": True},
            ["objects", "total_count"]
        )
        results['tests'].append(test_6)
        if test_6['status'] == 'PASS':
            results['passed'] += 1
            print(f"   ✅ Objects info retrieved ({test_6.get('duration_ms', 0)}ms)")
        else:
            results['failed'] += 1
            print(f"   ❌ Failed to get objects info: {test_6.get('error', 'Unknown')}")
        
        # Phase 7: Selection and Modification
        print(f"\n🎯 PHASE 6: Object Selection and Modification")
        
        # Select objects by layer
        test_7a = await self.test_mcp_tool_call(
            "select_rhino_objects",
            {"filters": {"layer": test_layer_name, "geometry_type": "Brep"}},
            ["status", "selected_count"]
        )
        results['tests'].append(test_7a)
        if test_7a['status'] == 'PASS':
            results['passed'] += 1
            print(f"   ✅ Objects selected by layer ({test_7a.get('duration_ms', 0)}ms)")
        else:
            results['failed'] += 1
            print(f"   ❌ Failed to select objects: {test_7a.get('error', 'Unknown')}")
        
        # Get information about currently selected objects
        test_7a2 = await self.test_mcp_tool_call(
            "get_rhino_selected_objects",
            {"include_lights": False, "include_grips": False},
            ["selected_objects", "count"]
        )
        results['tests'].append(test_7a2)
        if test_7a2['status'] == 'PASS':
            results['passed'] += 1
            print(f"   ✅ Selected objects info retrieved ({test_7a2.get('duration_ms', 0)}ms)")
        else:
            results['failed'] += 1
            print(f"   ❌ Failed to get selected objects info: {test_7a2.get('error', 'Unknown')}")
        
        # Modify objects with chained operations
        if created_object_ids:
            test_7b = await self.test_mcp_tool_call(
                "modify_rhino_objects",
                {
                    "targets": [
                        {"id": created_object_ids[0]},
                        {"name": "TestSphere_1"}
                    ],
                    "operations": [
                        {
                            "type": "rotate",
                            "angle": 45,
                            "axis": [0, 0, 1],
                            "center": "auto"
                        },
                        {
                            "type": "translate",
                            "vector": [2 * unit_scale_factor, 2 * unit_scale_factor, 0]
                        },
                        {
                            "type": "recolor",
                            "color": [100, 200, 255]
                        }
                    ],
                    "execution": "sequential"
                },
                ["status", "objects_modified", "execution_mode"]
            )
            results['tests'].append(test_7b)
            if test_7b['status'] == 'PASS':
                results['passed'] += 1
                print(f"   ✅ Objects modified with chained operations ({test_7b.get('duration_ms', 0)}ms)")
            else:
                results['failed'] += 1
                print(f"   ❌ Failed to modify objects: {test_7b.get('error', 'Unknown')}")
        else:
            # Fallback: try to modify by name only if no object IDs were captured
            print("   ⚠️  No object IDs available, attempting modify by object names only...")
            test_7b = await self.test_mcp_tool_call(
                "modify_rhino_objects",
                {
                    "targets": [
                        {"name": "TestBox_1"},
                        {"name": "TestSphere_1"}
                    ],
                    "operations": [
                        {
                            "type": "rotate",
                            "angle": 45,
                            "axis": [0, 0, 1],
                            "center": "auto"
                        },
                        {
                            "type": "translate",
                            "vector": [2 * unit_scale_factor, 2 * unit_scale_factor, 0]
                        },
                        {
                            "type": "recolor",
                            "color": [100, 200, 255]
                        }
                    ],
                    "execution": "sequential"
                },
                ["status", "objects_modified", "execution_mode"]
            )
            results['tests'].append(test_7b)
            if test_7b['status'] == 'PASS':
                results['passed'] += 1
                print(f"   ✅ Objects modified with chained operations (by name) ({test_7b.get('duration_ms', 0)}ms)")
            else:
                results['failed'] += 1
                print(f"   ❌ Failed to modify objects by name: {test_7b.get('error', 'Unknown')}")
        
        # Phase 8: Viewport Capture
        print(f"\n📸 PHASE 7: Viewport Capture")
        
        test_8 = await self.test_mcp_tool_call(
            "capture_rhino_viewport",
            {
                "layer": test_layer_name,
                "show_annotations": True,
                "max_size": 800
            },
            None  # Returns Image object
        )
        results['tests'].append(test_8)
        if test_8['status'] == 'PASS':
            results['passed'] += 1
            print(f"   ✅ Viewport captured ({test_8.get('duration_ms', 0)}ms)")
        else:
            results['failed'] += 1
            print(f"   ❌ Failed to capture viewport: {test_8.get('error', 'Unknown')}")
        
        # Phase 9: Complex Geometry via Script
        print(f"\n📜 PHASE 8: Script Execution for Complex Geometry")
        
        test_9 = await self.test_mcp_tool_call(
            "execute_rhinoscript",
            {
                "code": f'''
import rhinoscriptsyntax as rs
import math

# Create a complex spiral curve on test layer (scaled for units)
points = []
scale = {unit_scale_factor}
for i in range(101):
    t = i * 0.2
    x = (30 + 3 * math.cos(t) * (1 + 0.1 * t)) * scale
    y = (3 * math.sin(t) * (1 + 0.1 * t)) * scale
    z = (0.1 * t * t) * scale
    points.append([x, y, z])

# Create curve from points
curve_id = rs.AddCurve(points)
if curve_id:
    rs.ObjectLayer(curve_id, "{test_layer_name}")
    rs.ObjectName(curve_id, "IntegrationTest_Spiral")
    print("Created spiral curve: " + str(curve_id) + " (scale: " + str(scale) + ")")
else:
    print("Failed to create spiral curve")
'''
            },
            ["status", "output"]
        )
        results['tests'].append(test_9)
        if test_9['status'] == 'PASS':
            results['passed'] += 1
            print(f"   ✅ Complex geometry script executed ({test_9.get('duration_ms', 0)}ms)")
        else:
            results['failed'] += 1
            print(f"   ❌ Failed to execute script: {test_9.get('error', 'Unknown')}")
        
        # Phase 10: Final Scene Info
        print(f"\n📋 PHASE 9: Final Scene Assessment")
        
        test_10 = await self.test_mcp_tool_call(
            "get_rhino_scene_info",
            {},
            ["document_name", "total_objects", "total_layers"]
        )
        results['tests'].append(test_10)
        if test_10['status'] == 'PASS':
            results['passed'] += 1
            print(f"   ✅ Final scene info retrieved ({test_10.get('duration_ms', 0)}ms)")
        else:
            results['failed'] += 1
            print(f"   ❌ Failed to get final scene info: {test_10.get('error', 'Unknown')}")
        
        # Phase 11: Visual Inspection Before Cleanup
        print(f"\n👁️  PHASE 10: Visual Inspection")
        print("="*60)
        print("🔍 VISUAL INSPECTION REQUIRED")
        print("="*60)
        print()
        print("Please check your Rhino viewport now to verify the following objects were created:")
        print()
        print(f"📋 Expected objects on layer '{test_layer_name}' (scaled {unit_scale_factor}x for {document_units}):")
        print(f"  • TestBox_1 - A box at origin (0,0,0) - dimensions: {5*unit_scale_factor} x {3*unit_scale_factor} x {2*unit_scale_factor} - should be rotated and moved")
        print(f"  • TestSphere_1 - A sphere at ({10*unit_scale_factor},0,0) - radius: {2*unit_scale_factor} - should be rotated and moved")  
        print(f"  • TestCylinder_1 - A cylinder at ({20*unit_scale_factor},0,0) - radius: {1.5*unit_scale_factor}, height: {4*unit_scale_factor}")
        print(f"  • IntegrationTest_Spiral - A spiral curve starting around ({30*unit_scale_factor}, 0, 0) area (if script executed successfully)")
        print()
        print("🎨 Visual checks:")
        print("  • Objects should be visible on the integration test layer")
        print("  • Box and sphere should have blue color (100, 200, 255) from modification")
        print("  • Objects should be displaced from their original positions due to rotation + translation")
        print("  • Spiral curve should be visible at around (30, 0, 0) area")
        print()
        
        if created_object_ids:
            print(f"📝 Created object IDs for reference:")
            for i, obj_id in enumerate(created_object_ids):
                print(f"  {i+1}. {obj_id}")
        else:
            print("⚠️  No object IDs were captured (objects may still exist)")
        
        print()
        print("💡 Tip: You can use 'SelAll' command in Rhino to see all objects")
        print(f"💡 Tip: You can use 'SelLayer {test_layer_name}' to select only test objects")
        print()
        
        while True:
            user_input = input("✅ Can you see the expected objects in Rhino? (y/n/s): ").strip().lower()
            if user_input in ['y', 'yes']:
                print("✅ Visual inspection confirmed! Proceeding with cleanup...")
                break
            elif user_input in ['s', 'skip']:
                print("⏭️  Skipping visual inspection. Proceeding with cleanup...")
                break
            elif user_input in ['n', 'no']:
                print("❌ Objects not visible as expected.")
                retry = input("Would you like to continue with cleanup anyway? (y/n): ").strip().lower()
                if retry in ['y', 'yes']:
                    print("⚠️  Proceeding with cleanup despite visual issues...")
                    break
                else:
                    print("🛑 Test stopped. You can investigate the Rhino document manually.")
                    print("   Run the test again when ready, or use the quick mode for cleanup.")
                    return results
            else:
                print("Please enter 'y' for yes, 'n' for no, or 's' to skip inspection.")
        
        # Phase 12: Cleanup - Delete Objects
        print(f"\n🧹 PHASE 11: Cleanup Operations")
        
        test_11 = await self.test_mcp_tool_call(
            "delete_rhino_objects",
            {"all": True},
            ["status", "objects_deleted", "count"]
        )
        results['tests'].append(test_11)
        if test_11['status'] == 'PASS':
            results['passed'] += 1
            print(f"   ✅ Test objects deleted ({test_11.get('duration_ms', 0)}ms)")
        else:
            results['failed'] += 1
            print(f"   ❌ Failed to delete objects: {test_11.get('error', 'Unknown')}")
        
        # Phase 13: Cleanup - Delete Layer
        if test_layer_name:
            test_12 = await self.test_mcp_tool_call(
                "delete_rhino_layers",
                {"layers": [{"name": test_layer_name}]},
                ["status", "layers_deleted"]
            )
            results['tests'].append(test_12)
            if test_12['status'] == 'PASS':
                results['passed'] += 1
                print(f"   ✅ Testing layer deleted ({test_12.get('duration_ms', 0)}ms)")
            else:
                results['failed'] += 1
                print(f"   ❌ Failed to delete layer: {test_12.get('error', 'Unknown')}")
        
        print(f"\n🎉 Cleanup completed! Rhino document should be back to original state.")
        
        # Store all results
        for result in results['tests']:
            self.test_results.append(result)
        
        return results
    
    async def generate_test_report(self, test_results: Dict[str, Any]) -> None:
        """Generate comprehensive test report"""
        print("\n" + "="*80)
        print("📊 INTEGRATION TEST RESULTS")
        print("="*80)
        
        total_tests = test_results['passed'] + test_results['failed']
        success_rate = (test_results['passed'] / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\nOverall Results:")
        print(f"✅ Passed: {test_results['passed']}")
        print(f"❌ Failed: {test_results['failed']}")
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        # Detailed results
        print(f"\nDetailed Results:")
        for test in test_results['tests']:
            status_icon = "✅" if test['status'] == 'PASS' else "❌"
            duration = test.get('duration_ms', 0)
            print(f"  {status_icon} {test['tool']} ({duration}ms)")
            if test['status'] == 'FAIL':
                print(f"      Error: {test.get('error', 'Unknown')}")
        
        # Failed tests summary
        failed_tests = [t for t in test_results['tests'] if t['status'] == 'FAIL']
        if failed_tests:
            print(f"\n❌ Failed Tests Summary:")
            for test in failed_tests:
                print(f"  • {test['tool']}: {test.get('error', 'Unknown error')}")
        
        # Save detailed report
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "test_type": "integration_connected_flow",
            "server_url": self.server_url,
            "test_user_id": self.test_user_id,
            "license_data": self.license_data,
            "session_data": self.session_data,
            "summary": {
                "total_tests": total_tests,
                "passed": test_results['passed'],
                "failed": test_results['failed'],
                "success_rate": success_rate
            },
            "detailed_results": test_results['tests']
        }
        
        report_file = os.path.join(os.path.dirname(__file__), "integration_test_results.json")
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {report_file}")
    
    async def run_complete_integration_test(self) -> bool:
        """Run the complete integration test flow"""
        print("🚀 Starting Remote MCP Server Integration Test")
        print("=" * 80)
        print("This test will verify the complete connected flow:")
        print("• Server health and connectivity")
        print("• License generation and registration")
        print("• Session creation and management")
        print("• Real MCP tool calls with Rhino plugin")
        print()
        
        # Step 1: Check server
        print("Step 1: Checking server status...")
        if not await self.check_server_running():
            print("\n❌ Server is not running. Please start the server with:")
            print("   cd rhino_mcp_remote")
            print("   python -m remote_server.server")
            return False
        
        # Step 2: Clear previous test data
        print("\nStep 2: Clearing previous test data...")
        await self.clear_test_data()
        
        # Step 3: Generate license
        print("\nStep 3: Generating test license...")
        if not await self.generate_test_license():
            return False
        
        # Step 4: User registration
        print("\nStep 4: License registration...")
        if not self.prompt_user_license_registration():
            return False
        
        # Wait a moment for registration to process
        await asyncio.sleep(2)
        
        # Step 5: Verify registration
        print("\nStep 5: Verifying license registration...")
        if not await self.verify_license_registration():
            print("⚠️  License verification failed, but continuing with test...")
            print("💡 The test will still work if the license was registered correctly")
        
        # Step 6: Connection setup
        print("\nStep 6: Connection setup...")
        if not self.prompt_user_connection_setup():
            return False
        
        # Step 7: Find session
        print("\nStep 7: Finding active session...")
        if not await self.find_active_session():
            print("\n🔍 Debug Information:")
            await self._print_debug_info()
            return False
        
        # Step 8: Run MCP tool tests
        print("\nStep 8: Running MCP tool tests...")
        test_results = await self.run_mcp_tool_tests()
        
        # Step 9: Generate report
        await self.generate_test_report(test_results)
        
        # Final result
        success = test_results['failed'] == 0
        if success:
            print("\n🎉 All integration tests passed!")
        else:
            print(f"\n⚠️  {test_results['failed']} tests failed. See details above.")
        
        return success
    
    async def quick_test_tools(self) -> bool:
        """Quick test - find existing session and run tool tests directly"""
        print("🚀 Quick MCP Tool Test (using existing session)")
        print("=" * 60)
        
        # Step 1: Check server
        print("Step 1: Checking server status...")
        if not await self.check_server_running():
            print("\n❌ Server is not running. Please start the server first.")
            return False
        
        # Step 2: Find existing session
        print("\nStep 2: Looking for existing active session...")
        if not await self.find_active_session():
            print("\n❌ No active session found.")
            print("💡 To create a session:")
            print("   1. Make sure Rhino is open with RhinoMCP plugin loaded")
            print("   2. Run 'ReerStart' and choose 'remote' connection")
            print("   3. Use server URL: http://127.0.0.1:8080")
            return False
        
        # Step 3: Run tool tests
        print("\nStep 3: Running MCP tool tests...")
        test_results = await self.run_mcp_tool_tests()
        
        # Step 4: Generate report
        await self.generate_test_report(test_results)
        
        # Final result
        success = test_results['failed'] == 0
        if success:
            print("\n🎉 All tool tests passed!")
        else:
            print(f"\n⚠️  {test_results['failed']} tests failed. See details above.")
        
        return success
    
    async def _print_debug_info(self):
        """Print debug information to help diagnose connection issues"""
        try:
            async with aiohttp.ClientSession() as session:
                # Check server health
                async with session.get(f"{self.server_url}/health") as response:
                    if response.status == 200:
                        print("✅ Server is still running")
                    else:
                        print(f"❌ Server health check failed: {response.status}")
                
                # Check mock Redis data
                async with session.get(f"{self.server_url}/debug/mock-redis") as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"📊 Active sessions in memory: {data.get('active_sessions_count', 0)}")
                        print(f"📋 Session IDs: {data.get('active_sessions_list', [])}")
                        
                        conn_data = data.get('connection_manager', {}).get('data_summary', {})
                        sessions = conn_data.get('sessions', {})
                        licenses = conn_data.get('licenses', {})
                        
                        print(f"💾 Sessions in Redis: {len(sessions)}")
                        print(f"🔑 Licenses in Redis: {len(licenses)}")
                        
                        if sessions:
                            print("📝 Session details:")
                            for sid, sdata in sessions.items():
                                print(f"   {sid}: user={sdata.get('user_id')}, status={sdata.get('status')}")
                        
                        if licenses:
                            print("🔐 License details:")
                            for lid, ldata in licenses.items():
                                print(f"   {lid}: user={ldata.get('user_id')}, status={ldata.get('status')}")
                    else:
                        print(f"❌ Could not get debug info: {response.status}")
                
        except Exception as e:
            print(f"❌ Error getting debug info: {e}")


async def main():
    """Main entry point for integration testing"""
    # Check command line arguments
    quick_mode = len(sys.argv) > 1 and sys.argv[1].lower() in ['quick', 'tools', 'q', 't']
    
    if quick_mode:
        print("🧪 Quick MCP Tool Test")
        print("=" * 50)
        print("Testing MCP tools with existing session...")
        print()
        
        tester = ConnectedFlowTester()
        success = await tester.quick_test_tools()
        
    else:
        print("🧪 Remote MCP Server + Rhino Plugin Integration Test")
        print("=" * 80)
        print()
        
        # Check if user wants to proceed
        print("This test requires:")
        print("1. Remote MCP server running locally (http://127.0.0.1:8080)")
        print("2. Rhino with the RhinoMCP plugin loaded")
        print("3. User interaction for license registration and connection")
        print()
        print("💡 For quick tool testing only, run: python test_integration_connected_flow.py quick")
        print()
        
        proceed = input("Ready to proceed with full test? (y/n): ").strip().lower()
        if proceed not in ['y', 'yes']:
            print("Test cancelled by user.")
            return 1
        
        tester = ConnectedFlowTester()
        success = await tester.run_complete_integration_test()
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 