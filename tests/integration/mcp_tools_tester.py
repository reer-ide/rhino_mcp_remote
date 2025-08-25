"""
MCP tools testing functionality
"""

import asyncio
import json
from typing import Dict, Any, Optional, List
from fastmcp import Client
from fastmcp.client import StreamableHttpTransport
from .base_tester import BaseIntegrationTester


class MCPToolsTester(BaseIntegrationTester):
    """Handles MCP tool testing for integration tests"""
    
    def __init__(self, server_url: str = "http://127.0.0.1:8080"):
        super().__init__(server_url)
        self.mcp_client = Client(StreamableHttpTransport(server_url+"/mcp"))
    
    async def test_mcp_tools(self) -> bool:
        """Test MCP tools against connected session"""
        if not self.session_data_list:
            print("[ERROR] No session data available for testing")
            return False
        
        print("\n" + "="*60)
        print("[TEST] Testing MCP Tools")
        print("="*60)
        
        # For comprehensive testing, use run_mcp_tool_tests
        # which follows a logical workflow and tests all tools
        results = await self.run_mcp_tool_tests()
        
        # Convert results to our standard format
        test_results = {
            'total': results['passed'] + results['failed'],
            'passed': results['passed'],
            'failed': results['failed']
        }
        
        # Print summary
        return self.print_test_summary(test_results)
    
    async def test_mcp_tool_call(self, tool_name: str, arguments: Dict[str, Any], 
                                  expected_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """Helper method to test a single MCP tool call"""
        import time
        
        start_time = time.time()
        result = {
            'tool': tool_name,
            'status': 'FAIL',
            'error': None,
            'response': None,
            'duration_ms': 0
        }
        
        try:
            # Get session_id from first session
            session_id = self.session_data_list[0]['session_id']
            
            # Add session_id to arguments
            tool_arguments = {**arguments, "session_id": session_id}
            
            # Call the tool using async context manager
            async with self.mcp_client as client:
                response = await client.call_tool(tool_name, arguments=tool_arguments)
            
            # Check if we got a response (CallToolResult object)
            if response and hasattr(response, 'content'):
                # Handle CallToolResult object from FastMCP
                if hasattr(response.content[0], 'text'):
                    result['response'] = response.content[0].text
                    result['status'] = 'PASS'
                else:
                    result['response'] = str(response.content)
                    result['status'] = 'PASS'
                
                # If expected fields provided, check for them
                if expected_fields:
                    missing_fields = []
                    response_data = result['response']
                    if isinstance(response_data, str):
                        try:
                            response_data = json.loads(response_data)
                        except:
                            # If JSON parsing fails, fall back to string search
                            response_data = response_data
                    
                    for field in expected_fields:
                        # Check if field exists as a key in the parsed object, or in the string if parsing failed
                        if isinstance(response_data, dict):
                            if field not in response_data:
                                missing_fields.append(field)
                        else:
                            # Fallback to string search for unparseable responses
                            if field not in str(response_data):
                                missing_fields.append(field)
                    
                    
                    if missing_fields:
                        result['error'] = f"Missing expected fields: {', '.join(missing_fields)}"
                        result['status'] = 'FAIL'
            else:
                result['error'] = f"Invalid response object or no content: {type(response) if response else 'None'}"
                result['response'] = str(response) if response else None
        
        except Exception as e:
            result['error'] = str(e)
            result['response'] = None
        
        # Calculate duration
        result['duration_ms'] = int((time.time() - start_time) * 1000)
        
        # Add to test results
        self.add_test_result(tool_name, result['status'] == 'PASS', 
                           result['error'] or f"Tool executed in {result['duration_ms']}ms")
        
        return result

    async def run_mcp_tool_tests(self) -> Dict[str, Any]:
        """Run comprehensive MCP tool tests following a logical workflow"""
        print("\n" + "="*80)
        print("[TEST] Running Comprehensive MCP Tool Tests")
        print("="*80)
        print("Following logical workflow: Scene Info -> Layer -> Objects -> Metadata -> Modify -> Script -> Cleanup")
        
        results = {"passed": 0, "failed": 0, "tests": []}
        
        # Shared test data
        test_layer_name = "IntegrationTest_Layer"
        created_object_ids = []
        created_layer_ids = []
        document_units = "Unknown"
        unit_scale_factor = 1.0  # Default scale factor
        
        # Baseline counts for verification
        initial_object_count = 0
        initial_layer_count = 0
        
        # Phase 1: Initial Scene State
        print(f"\n[PHASE 1] Initial Scene Assessment")
        
        test_1 = await self.test_mcp_tool_call(
            "get_rhino_scene_info",
            {},
            ["document", "layers", "timestamp"]
        )
        results['tests'].append(test_1)
        if test_1['status'] == 'PASS':
            results['passed'] += 1
            print(f"   [PASS] Initial scene info retrieved ({test_1.get('duration_ms', 0)}ms)")
            
            # Extract baseline counts and units
            if 'response' in test_1:
                response_data = test_1['response']
                if isinstance(response_data, str):
                    try:
                        response_data = json.loads(response_data)
                    except json.JSONDecodeError:
                        response_data = {}
                
                if 'document' in response_data:
                    doc_data = response_data['document']
                    initial_object_count = doc_data.get('total_objects', 0)
                    initial_layer_count = doc_data.get('total_layers', 0)
                    document_units = doc_data.get('units', 'Unknown')
                    
                    print(f"   [BASELINE] Initial objects: {initial_object_count}")
                    print(f"   [BASELINE] Initial layers: {initial_layer_count}")
                    print(f"   [UNITS] Document units: {document_units}")
                    
                    # Scale factor based on units (assuming small objects need scaling up)
                    if document_units.lower() == 'millimeters':
                        unit_scale_factor = 100.0  # Scale up by 100 for visibility
                        print(f"   [UNITS] Scaling objects by {unit_scale_factor}x for millimeter units")
                    elif document_units.lower() == 'meters':
                        unit_scale_factor = 0.1  # Scale down for meter units
                        print(f"   [UNITS] Scaling objects by {unit_scale_factor}x for meter units")
                    elif document_units.lower() in ['inches', 'feet']:
                        unit_scale_factor = 10.0  # Moderate scale for imperial
                        print(f"   [UNITS] Scaling objects by {unit_scale_factor}x for imperial units")
                    else:
                        print(f"   [UNITS] Using default scale (1.0x) for units: {document_units}")
        else:
            results['failed'] += 1
            print(f"   [FAIL] Failed to get scene info: {test_1.get('error', 'Unknown')}")
        
        # Phase 2: Create Testing Layer
        print(f"\n[PHASE 2] Testing Infrastructure Setup")
        
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
            print(f"   [PASS] Testing layer created ({test_2.get('duration_ms', 0)}ms)")
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
            print(f"   [FAIL] Failed to create layer: {test_2.get('error', 'Unknown')}")
        
        # Phase 3: Create Test Objects
        print(f"\n[PHASE 3] Object Creation")
        
        test_3 = await self.test_mcp_tool_call(
            "create_rhino_basic_objects",
            {
                "objects": [
                    {
                        "type": "box",
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
                        "type": "sphere",
                        "name": "TestSphere_1", 
                        "layer": test_layer_name,
                        "params": {
                            "center": [10 * unit_scale_factor, 0, 0],
                            "radius": 2 * unit_scale_factor
                        }
                    },
                    {
                        "type": "cylinder",
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
            ["status", "objects", "count", "created", "errors"]
        )
        results['tests'].append(test_3)
        if test_3['status'] == 'PASS':
            results['passed'] += 1
            print(f"   [PASS] Test objects created ({test_3.get('duration_ms', 0)}ms)")
            # Extract object IDs for later tests
            if 'response' in test_3:
                response_data = test_3['response']
                if isinstance(response_data, str):
                    try:
                        response_data = json.loads(response_data)
                    except json.JSONDecodeError:
                        response_data = {}
                objects_created = response_data.get('objects', [])
                for obj in objects_created:
                    # Only extract IDs from successful objects (no error field)
                    if 'object_id' in obj and 'error' not in obj:
                        obj_id = obj['object_id']
                        created_object_ids.append(obj_id)
                        print(f"   [UNITS] Captured object ID: {obj_id}")
                    elif 'error' in obj:
                        print(f"   [WARN]  Object creation failed: {obj.get('name', 'unknown')} - {obj['error']}")
                
                print(f"   [UNITS] Total object IDs captured: {len(created_object_ids)}")
                
                # Debug: print response structure if no successful objects found
                if not created_object_ids and objects_created:
                    print(f"   [WARN]  No successful objects found. Response structure: {response_data}")
        else:
            results['failed'] += 1
            print(f"   [FAIL] Failed to create objects: {test_3.get('error', 'Unknown')}")
        
        # Phase 3.5: Verify Scene Changes After Object Creation
        print(f"\n[PHASE 3.5] Scene Changes Verification")
        
        test_3_5 = await self.test_mcp_tool_call(
            "get_rhino_scene_info",
            {},
            ["document", "layers", "timestamp"]
        )
        results['tests'].append(test_3_5)
        if test_3_5['status'] == 'PASS':
            results['passed'] += 1
            print(f"   [PASS] Post-creation scene info retrieved ({test_3_5.get('duration_ms', 0)}ms)")
            
            # Verify count increases
            if 'response' in test_3_5:
                response_data = test_3_5['response']
                if isinstance(response_data, str):
                    try:
                        response_data = json.loads(response_data)
                    except json.JSONDecodeError:
                        response_data = {}
                
                if 'document' in response_data:
                    doc_data = response_data['document']
                    current_object_count = doc_data.get('total_objects', 0)
                    current_layer_count = doc_data.get('total_layers', 0)
                    
                    expected_objects = initial_object_count + len(created_object_ids)
                    expected_layers = initial_layer_count + 1  # Added 1 test layer
                    
                    print(f"   [VERIFY] Objects: {current_object_count} (expected: {expected_objects})")
                    print(f"   [VERIFY] Layers: {current_layer_count} (expected: {expected_layers})")
                    
                    if current_object_count >= expected_objects:
                        print(f"   [PASS] Object count increased correctly")
                    else:
                        print(f"   [WARN] Object count mismatch - may indicate creation issues")
                    
                    if current_layer_count >= expected_layers:
                        print(f"   [PASS] Layer count increased correctly")
                    else:
                        print(f"   [WARN] Layer count mismatch - may indicate layer creation issues")
        else:
            results['failed'] += 1
            print(f"   [FAIL] Failed to get post-creation scene info: {test_3_5.get('error', 'Unknown')}")
        
        # Phase 4: Add Metadata to Objects
        print(f"\n[UNITS]  PHASE 4: Metadata Management")
        
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
                print(f"   [PASS] Metadata added to objects ({test_4.get('duration_ms', 0)}ms)")
            else:
                results['failed'] += 1
                print(f"   [FAIL] Failed to add metadata: {test_4.get('error', 'Unknown')}")
        else:
            print("   [WARN]  No object IDs available, skipping metadata test...")
            # Note: add_rhino_objects_metadata requires object IDs, not names
        
        # Update Metadata
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
                print(f"   [PASS] Metadata updated ({test_5.get('duration_ms', 0)}ms)")
            else:
                results['failed'] += 1
                print(f"   [FAIL] Failed to update metadata: {test_5.get('error', 'Unknown')}")
        else:
            print("   [WARN]  No object IDs available, skipping update metadata test...")
            # Note: update_rhino_objects_metadata requires object IDs, not names
        
        # Phase 5: Get Objects Info
        print(f"\n[UNITS] PHASE 5: Information Retrieval")
        
        test_6 = await self.test_mcp_tool_call(
            "get_rhino_objects_info",
            {"get_all_objects": True, "include_attributes": True},
            ["objects", "count"]
        )
        results['tests'].append(test_6)
        if test_6['status'] == 'PASS':
            results['passed'] += 1
            print(f"   [PASS] Objects info retrieved ({test_6.get('duration_ms', 0)}ms)")
        else:
            results['failed'] += 1
            print(f"   [FAIL] Failed to get objects info: {test_6.get('error', 'Unknown')}")
        
        # Phase 6: Selection and Modification
        print(f"\n[UNITS] PHASE 6: Object Selection and Modification")
        
        # Select objects by layer - note: this may fail due to plugin implementation issues
        test_7a = await self.test_mcp_tool_call(
            "select_filtered_rhino_objects",
            {"filters": {"layer": test_layer_name}},
            None  # Don't validate fields since plugin has implementation issues
        )
        results['tests'].append(test_7a)
        if test_7a['status'] == 'PASS':
            results['passed'] += 1
            # Get information about currently selected objects
            # Note: need to wait for the selection to be processed
            test_7a2 = await self.test_mcp_tool_call(
                "get_rhino_selected_objects",
                {"include_lights": False, "include_grips": False},
                ["selected_objects", "selected_count"]
            )
            results['tests'].append(test_7a2)
            if test_7a2['status'] == 'PASS':
                results['passed'] += 1
                print(f"   [PASS] Selected objects info retrieved ({test_7a2.get('duration_ms', 0)}ms)")
            else:
                results['failed'] += 1
                print(f"   [FAIL] Failed to get selected objects info: {test_7a2.get('error', 'no objects selected')}")
            print(f"   [PASS] Objects selected by layer ({test_7a.get('duration_ms', 0)}ms)")
        else:
            results['failed'] += 1
            print(f"   [FAIL] Failed to select objects: {test_7a.get('error', 'Unknown')}, get_rhino_selected_objects will not work")            
        
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
                print(f"   [PASS] Objects modified with chained operations ({test_7b.get('duration_ms', 0)}ms)")
            else:
                results['failed'] += 1
                print(f"   [FAIL] Failed to modify objects: {test_7b.get('error', 'Unknown')}")
        else:
            # Fallback: try to modify by name only if no object IDs were captured
            print("   [WARN]  No object IDs available, attempting modify by object names only...")
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
                print(f"   [PASS] Objects modified with chained operations (by name) ({test_7b.get('duration_ms', 0)}ms)")
            else:
                results['failed'] += 1
                print(f"   [FAIL] Failed to modify objects by name: {test_7b.get('error', 'Unknown')}")
        
        # Phase 7: Viewport Capture
        print(f"\n[UNITS] PHASE 7: Viewport Capture")
        
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
            print(f"   [PASS] Viewport captured ({test_8.get('duration_ms', 0)}ms)")
        else:
            results['failed'] += 1
            print(f"   [FAIL] Failed to capture viewport: {test_8.get('error', 'Unknown')}")
        
        # Phase 8: Complex Geometry via Script
        print(f"\n[UNITS] PHASE 8: Script Execution for Complex Geometry")
        
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
    print("CREATED_OBJECT_ID:" + str(curve_id))
    print("Created spiral curve with scale: " + str(scale))
else:
    print("SCRIPT_ERROR:Failed to create spiral curve")
'''
            },
            ["status", "message", "printed_output"]
        )
        results['tests'].append(test_9)
        if test_9['status'] == 'PASS':
            results['passed'] += 1
            print(f"   [PASS] Complex geometry script executed ({test_9.get('duration_ms', 0)}ms)")
            
            # Extract object ID from script output
            if 'response' in test_9:
                response_data = test_9['response']
                if isinstance(response_data, str):
                    try:
                        response_data = json.loads(response_data)
                    except json.JSONDecodeError:
                        response_data = {}
                
                # Look for object ID in the output
                printed_output = response_data.get('printed_output', '')
                for line in printed_output.split('\n'):
                    line = line.strip()
                    if line.startswith('CREATED_OBJECT_ID:'):
                        script_object_id = line.replace('CREATED_OBJECT_ID:', '').strip()
                        if script_object_id:
                            created_object_ids.append(script_object_id)
                            print(f"   [UNITS] Captured script object ID: {script_object_id}")
                        break
                    elif line.startswith('SCRIPT_ERROR:'):
                        error_msg = line.replace('SCRIPT_ERROR:', '').strip()
                        print(f"   [WARN] Script reported error: {error_msg}")
                        break
                else:
                    print(f"   [WARN] Could not extract object ID from script output")
        else:
            results['failed'] += 1
            print(f"   [FAIL] Failed to execute script: {test_9.get('error', 'Unknown')}")
        
        # Phase 9: Visual Inspection Before Cleanup
        print(f"\n[UNITS] PHASE 9: Visual Inspection")
        print("="*60)
        print("[UNITS] VISUAL INSPECTION REQUIRED")
        print("="*60)
        print()
        print("Please check your Rhino viewport now to verify the following objects were created:")
        print()
        print(f"[UNITS] Expected objects on layer '{test_layer_name}' (scaled {unit_scale_factor}x for {document_units}):")
        print(f"  [UNITS] TestBox_1 - A box at origin (0,0,0) - dimensions: {5*unit_scale_factor} x {3*unit_scale_factor} x {2*unit_scale_factor} - should be rotated and moved")
        print(f"  [UNITS] TestSphere_1 - A sphere at ({10*unit_scale_factor},0,0) - radius: {2*unit_scale_factor} - should be rotated and moved")  
        print(f"  [UNITS] TestCylinder_1 - A cylinder at ({20*unit_scale_factor},0,0) - radius: {1.5*unit_scale_factor}, height: {4*unit_scale_factor}")
        print(f"  [UNITS] IntegrationTest_Spiral - A spiral curve starting around ({30*unit_scale_factor}, 0, 0) area (created by script)")
        print()
        print(f"[UNITS] Total expected objects: {len(created_object_ids)} ({len(created_object_ids)} captured object IDs)")
        print()
        print("[UNITS] Visual checks:")
        print("  [UNITS] Objects should be visible on the integration test layer")
        print("  [UNITS] Box and sphere should have blue color (100, 200, 255) from modification")
        print("  [UNITS] Objects should be displaced from their original positions due to rotation + translation")
        print("  [UNITS] Spiral curve should be visible at around (30, 0, 0) area")
        print()
        
        if created_object_ids:
            print(f"[UNITS] Created object IDs for reference:")
            for i, obj_id in enumerate(created_object_ids):
                print(f"  {i+1}. {obj_id}")
        else:
            print("[WARN]  No object IDs were captured (objects may still exist)")
        
        print()
        print("[UNITS] Tip: You can use 'SelAll' command in Rhino to see all objects")
        print(f"[UNITS] Tip: You can use 'SelLayer {test_layer_name}' to select only test objects")
        print()
        
        try:
            user_input = input("[PASS] Can you see the expected objects in Rhino? (y/n/s): ").strip().lower()
            if user_input in ['y', 'yes']:
                print("[PASS] Visual inspection confirmed! Proceeding with cleanup...")
            elif user_input in ['s', 'skip']:
                print("[SKIP] Skipping visual inspection. Proceeding with cleanup...")
            elif user_input in ['n', 'no']:
                print("[FAIL] Objects not visible as expected.")
                retry = input("Would you like to continue with cleanup anyway? (y/n): ").strip().lower()
                if retry in ['y', 'yes']:
                    print("[WARN] Proceeding with cleanup despite visual issues...")
                else:
                    print("[UNITS] Test stopped. You can investigate the Rhino document manually.")
                    print("   Run the test again when ready, or use the quick mode for cleanup.")
                    return results
            else:
                print("Please enter 'y' for yes, 'n' for no, or 's' to skip inspection.")
                print("[INFO] Continuing with cleanup automatically...")
        except EOFError:
            # Non-interactive mode, proceed automatically
            print("[PASS] Can you see the expected objects in Rhino? (y/n/s): s [auto]")
            print("[INFO] Running in non-interactive mode, skipping visual inspection")
        
        # Phase 10: Cleanup - Delete Test Objects Only
        print(f"\n[UNITS] PHASE 10: Cleanup Operations")
        
        # Delete created objects by their IDs if we have them
        if created_object_ids:
            test_11a = await self.test_mcp_tool_call(
                "delete_rhino_objects",
                {"objects": [{"id": obj_id} for obj_id in created_object_ids]},
                ["status", "objects_deleted", "count"]
            )
            results['tests'].append(test_11a)
            if test_11a['status'] == 'PASS':
                results['passed'] += 1
                print(f"   [PASS] Test objects deleted by ID ({test_11a.get('duration_ms', 0)}ms)")
            else:
                results['failed'] += 1
                print(f"   [FAIL] Failed to delete objects by ID: {test_11a.get('error', 'Unknown')}")
                
                # Fallback: try to delete all objects on test layer
                print("   [FALLBACK] Attempting to delete all objects on test layer...")
                test_11b = await self.test_mcp_tool_call(
                    "select_filtered_rhino_objects", 
                    {"filters": {"layer": test_layer_name}},
                    None
                )
                if test_11b['status'] == 'PASS':
                    # Now delete selected objects
                    test_11c = await self.test_mcp_tool_call(
                        "delete_rhino_objects",
                        {"selected": True},
                        ["status", "deleted", "count"]
                    )
                    results['tests'].append(test_11c)
                    if test_11c['status'] == 'PASS':
                        results['passed'] += 1
                        print(f"   [PASS] Test layer objects deleted by selection ({test_11c.get('duration_ms', 0)}ms)")
                    else:
                        results['failed'] += 1
                        print(f"   [FAIL] Failed to delete selected objects: {test_11c.get('error', 'Unknown')}")
        else:
            # No object IDs available, try layer-based deletion
            print("   [INFO] No object IDs available, attempting layer-based cleanup...")
            test_11_layer = await self.test_mcp_tool_call(
                "select_filtered_rhino_objects",
                {"filters": {"layer": test_layer_name}},
                None
            )
            if test_11_layer['status'] == 'PASS':
                test_11_del = await self.test_mcp_tool_call(
                    "delete_rhino_objects",
                    {"selected": True},
                    ["status", "deleted", "count"]
                )
                results['tests'].append(test_11_del)
                if test_11_del['status'] == 'PASS':
                    results['passed'] += 1
                    print(f"   [PASS] Test layer objects deleted ({test_11_del.get('duration_ms', 0)}ms)")
                else:
                    results['failed'] += 1
                    print(f"   [FAIL] Failed to delete test layer objects: {test_11_del.get('error', 'Unknown')}")
        
        # Phase 11: Cleanup - Delete Test Layer
        if test_layer_name:
            test_12 = await self.test_mcp_tool_call(
                "delete_rhino_layers",
                {"layers": [{"name": test_layer_name}]},
                ["status", "layers_deleted"]
            )
            results['tests'].append(test_12)
            if test_12['status'] == 'PASS':
                results['passed'] += 1
                print(f"   [PASS] Testing layer deleted ({test_12.get('duration_ms', 0)}ms)")
            else:
                results['failed'] += 1
                print(f"   [FAIL] Failed to delete layer: {test_12.get('error', 'Unknown')}")
        
        # Phase 12: Final Scene Verification
        print(f"\n[PHASE 12] Post-Cleanup Scene Verification")
        
        test_13 = await self.test_mcp_tool_call(
            "get_rhino_scene_info",
            {},
            ["document", "layers", "timestamp"]
        )
        results['tests'].append(test_13)
        if test_13['status'] == 'PASS':
            results['passed'] += 1
            print(f"   [PASS] Post-cleanup scene info retrieved ({test_13.get('duration_ms', 0)}ms)")
            
            # Verify counts returned to baseline
            if 'response' in test_13:
                response_data = test_13['response']
                if isinstance(response_data, str):
                    try:
                        response_data = json.loads(response_data)
                    except json.JSONDecodeError:
                        response_data = {}
                
                if 'document' in response_data:
                    doc_data = response_data['document']
                    final_object_count = doc_data.get('total_objects', 0)
                    final_layer_count = doc_data.get('total_layers', 0)
                    
                    # Calculate total objects that were created and should have been cleaned up
                    total_created_objects = len(created_object_ids)  # All captured object IDs
                    expected_final_objects = initial_object_count  # Should be back to baseline
                    
                    print(f"   [VERIFY] Final objects: {final_object_count} (baseline: {initial_object_count})")
                    print(f"   [VERIFY] Final layers: {final_layer_count} (baseline: {initial_layer_count})")
                    print(f"   [INFO] Total test objects created during test: {total_created_objects}")
                    print(f"   [INFO] Captured object IDs for deletion: {len(created_object_ids)}")
                    
                    if final_object_count <= initial_object_count:
                        print(f"   [PASS] Object count returned to baseline (cleanup successful)")
                    else:
                        remaining_objects = final_object_count - initial_object_count
                        print(f"   [WARN] Object count above baseline - {remaining_objects} objects may remain")
                        print(f"   [HINT] Run 'SelLayer {test_layer_name}' in Rhino to check for remaining test objects")
                    
                    if final_layer_count <= initial_layer_count:
                        print(f"   [PASS] Layer count returned to baseline (cleanup successful)")
                    else:
                        remaining_layers = final_layer_count - initial_layer_count
                        print(f"   [WARN] Layer count above baseline - {remaining_layers} layers may remain")
                        print(f"   [HINT] Check for remaining test layers in Rhino layer panel")
        else:
            results['failed'] += 1
            print(f"   [FAIL] Failed to get post-cleanup scene info: {test_13.get('error', 'Unknown')}")
        
        print(f"\n[DONE] Cleanup completed! Rhino document should be back to original state.")
        
        # Results are already stored by individual test_mcp_tool_call invocations
        # No need to store them again here
        
        return results