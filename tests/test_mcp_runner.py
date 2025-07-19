#!/usr/bin/env python3
"""
Master Test Runner for Remote MCP Server Tool Testing
Runs comprehensive tests for all MCP tools using FastMCP in-memory testing.
"""

import pytest
import asyncio
import json
import sys
import os
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock, AsyncMock

# Add the parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastmcp import Client
from remote_server.server import mcp


class MCPTestRunner:
    """Master test runner for MCP tools using FastMCP in-memory testing"""
    
    def __init__(self):
        self.test_results = {}
        self.session_id = "test-runner-session-123"
        self.mock_connection_manager = None
        
    def setup_mock_connection_manager(self):
        """Setup mock connection manager for testing"""
        # Create mock session
        mock_session = MagicMock()
        mock_session.session_id = self.session_id
        mock_session.user_id = "test-runner-user"
        mock_session.status = "active"
        mock_session.instance_id = "test-instance-456"
        
        # Patch the connection manager
        patcher = patch('remote_server.server.connection_manager')
        mock_cm = patcher.start()
        
        # Setup async mock methods
        mock_cm.get_session = AsyncMock(return_value=mock_session)
        mock_cm.send_to_rhino = AsyncMock()
        
        self.mock_connection_manager = mock_cm
        return patcher
    
    async def test_scene_info_tools(self) -> Dict[str, Any]:
        """Test scene information tools"""
        print("Testing Scene Information Tools...")
        results = {"passed": 0, "failed": 0, "tests": []}
        
        # Mock scene data
        mock_scene_data = {
            "name": "test_runner.3dm",
            "total_objects": 25,
            "total_layers": 4,
            "layers": [
                {
                    "full_path": "Default",
                    "object_count": 15,
                    "is_visible": True,
                    "example_objects": [
                        {"id": "obj1", "name": "Test Object 1", "type": "Point"}
                    ]
                }
            ]
        }
        
        self.mock_connection_manager.send_to_rhino.return_value = mock_scene_data
        
        client = Client(mcp)
        async with client:
            try:
                # Test get_rhino_scene_info
                result = await client.call_tool("get_rhino_scene_info", {
                    "session_id": self.session_id
                })
                
                response_data = json.loads(result.content[0].text)
                assert response_data["name"] == "test_runner.3dm"
                assert response_data["total_objects"] == 25
                
                results["passed"] += 1
                results["tests"].append({
                    "name": "get_rhino_scene_info",
                    "status": "PASS",
                    "message": "Scene info retrieved successfully"
                })
                print("  ✓ get_rhino_scene_info: PASS")
                
            except Exception as e:
                results["failed"] += 1
                results["tests"].append({
                    "name": "get_rhino_scene_info",
                    "status": "FAIL", 
                    "message": str(e)
                })
                print(f"  ✗ get_rhino_scene_info: FAIL - {e}")
        
        # Test get_rhino_objects_info
        mock_objects_data = {
            "objects": [
                {
                    "id": "obj1",
                    "name": "Test Point", 
                    "type": "Point",
                    "layer": "Default",
                    "metadata": {"description": "Test object"}
                }
            ],
            "total_count": 1
        }
        
        self.mock_connection_manager.send_to_rhino.return_value = mock_objects_data
        
        async with client:
            try:
                result = await client.call_tool("get_rhino_objects_info", {
                    "session_id": self.session_id,
                    "object_type": "Point",
                    "with_metadata": True
                })
                
                response_data = json.loads(result.content[0].text)
                assert len(response_data["objects"]) == 1
                assert response_data["objects"][0]["type"] == "Point"
                
                results["passed"] += 1
                results["tests"].append({
                    "name": "get_rhino_objects_info",
                    "status": "PASS",
                    "message": "Objects info retrieved with filters"
                })
                print("  ✓ get_rhino_objects_info: PASS")
                
            except Exception as e:
                results["failed"] += 1
                results["tests"].append({
                    "name": "get_rhino_objects_info",
                    "status": "FAIL",
                    "message": str(e)
                })
                print(f"  ✗ get_rhino_objects_info: FAIL - {e}")
        
        return results
    
    async def test_object_creation_tools(self) -> Dict[str, Any]:
        """Test object creation tools"""
        print("Testing Object Creation Tools...")
        results = {"passed": 0, "failed": 0, "tests": []}
        
        creation_tests = [
            {
                "name": "create_point",
                "params": {
                    "geometry_type": "point",
                    "point": {"x": 0, "y": 0, "z": 0},
                    "name": "Test Point"
                },
                "mock_response": {
                    "status": "success",
                    "object_ids": ["test_point_123"],
                    "objects_created": 1
                }
            },
            {
                "name": "create_sphere",
                "params": {
                    "geometry_type": "sphere",
                    "center": {"x": 5, "y": 5, "z": 5},
                    "radius": 3,
                    "name": "Test Sphere"
                },
                "mock_response": {
                    "status": "success",
                    "object_ids": ["test_sphere_456"],
                    "objects_created": 1
                }
            },
            {
                "name": "create_batch",
                "params": {
                    "objects": [
                        {
                            "geometry_type": "point",
                            "point": {"x": i, "y": i, "z": 0},
                            "name": f"Batch Point {i}"
                        } for i in range(3)
                    ]
                },
                "mock_response": {
                    "status": "success",
                    "object_ids": ["batch_1", "batch_2", "batch_3"],
                    "objects_created": 3
                }
            }
        ]
        
        client = Client(mcp)
        for test in creation_tests:
            self.mock_connection_manager.send_to_rhino.return_value = test["mock_response"]
            
            async with client:
                try:
                    result = await client.call_tool("create_rhino_basic_objects", {
                        "session_id": self.session_id,
                        **test["params"]
                    })
                    
                    response_data = json.loads(result.content[0].text)
                    assert response_data["status"] == "success"
                    assert response_data["objects_created"] == test["mock_response"]["objects_created"]
                    
                    results["passed"] += 1
                    results["tests"].append({
                        "name": test["name"],
                        "status": "PASS",
                        "message": f"Created {response_data['objects_created']} objects"
                    })
                    print(f"  ✓ {test['name']}: PASS")
                    
                except Exception as e:
                    results["failed"] += 1
                    results["tests"].append({
                        "name": test["name"],
                        "status": "FAIL",
                        "message": str(e)
                    })
                    print(f"  ✗ {test['name']}: FAIL - {e}")
        
        return results
    
    async def test_object_manipulation_tools(self) -> Dict[str, Any]:
        """Test object manipulation tools"""
        print("Testing Object Manipulation Tools...")
        results = {"passed": 0, "failed": 0, "tests": []}
        
        manipulation_tests = [
            {
                "tool": "select_rhino_objects",
                "name": "select_objects",
                "params": {
                    "object_ids": ["obj1", "obj2"]
                },
                "mock_response": {
                    "status": "success",
                    "selected_count": 2,
                    "selected_objects": ["obj1", "obj2"]
                }
            },
            {
                "tool": "modify_rhino_objects",
                "name": "translate_objects",
                "params": {
                    "object_ids": ["obj1"],
                    "transformation": {
                        "type": "translate",
                        "vector": {"x": 10, "y": 5, "z": 0}
                    }
                },
                "mock_response": {
                    "status": "success",
                    "modified_objects": ["obj1"],
                    "modification_count": 1
                }
            },
            {
                "tool": "delete_rhino_objects",
                "name": "delete_objects",
                "params": {
                    "object_ids": ["obj1", "obj2"]
                },
                "mock_response": {
                    "status": "success",
                    "deleted_objects": ["obj1", "obj2"],
                    "deletion_count": 2
                }
            }
        ]
        
        client = Client(mcp)
        for test in manipulation_tests:
            self.mock_connection_manager.send_to_rhino.return_value = test["mock_response"]
            
            async with client:
                try:
                    result = await client.call_tool(test["tool"], {
                        "session_id": self.session_id,
                        **test["params"]
                    })
                    
                    response_data = json.loads(result.content[0].text)
                    assert response_data["status"] == "success"
                    
                    results["passed"] += 1
                    results["tests"].append({
                        "name": test["name"],
                        "status": "PASS",
                        "message": f"Tool {test['tool']} executed successfully"
                    })
                    print(f"  ✓ {test['name']}: PASS")
                    
                except Exception as e:
                    results["failed"] += 1
                    results["tests"].append({
                        "name": test["name"],
                        "status": "FAIL",
                        "message": str(e)
                    })
                    print(f"  ✗ {test['name']}: FAIL - {e}")
        
        return results
    
    async def test_layer_management_tools(self) -> Dict[str, Any]:
        """Test layer management tools"""
        print("Testing Layer Management Tools...")
        results = {"passed": 0, "failed": 0, "tests": []}
        
        # Test create_rhino_layers
        self.mock_connection_manager.send_to_rhino.return_value = {
            "status": "success",
            "created_layers": ["TestLayer1", "TestLayer2"],
            "layers_created": 2
        }
        
        client = Client(mcp)
        async with client:
            try:
                result = await client.call_tool("create_rhino_layers", {
                    "session_id": self.session_id,
                    "layers": [
                        {"name": "TestLayer1", "color": {"r": 255, "g": 0, "b": 0}},
                        {"name": "TestLayer2", "color": {"r": 0, "g": 255, "b": 0}}
                    ]
                })
                
                response_data = json.loads(result.content[0].text)
                assert response_data["status"] == "success"
                assert response_data["layers_created"] == 2
                
                results["passed"] += 1
                results["tests"].append({
                    "name": "create_layers",
                    "status": "PASS",
                    "message": "Created 2 layers successfully"
                })
                print("  ✓ create_rhino_layers: PASS")
                
            except Exception as e:
                results["failed"] += 1
                results["tests"].append({
                    "name": "create_layers",
                    "status": "FAIL",
                    "message": str(e)
                })
                print(f"  ✗ create_rhino_layers: FAIL - {e}")
        
        # Test delete_rhino_layers
        self.mock_connection_manager.send_to_rhino.return_value = {
            "status": "success",
            "deleted_layers": ["TestLayer1", "TestLayer2"],
            "layers_deleted": 2
        }
        
        async with client:
            try:
                result = await client.call_tool("delete_rhino_layers", {
                    "session_id": self.session_id,
                    "layer_names": ["TestLayer1", "TestLayer2"]
                })
                
                response_data = json.loads(result.content[0].text)
                assert response_data["status"] == "success"
                assert response_data["layers_deleted"] == 2
                
                results["passed"] += 1
                results["tests"].append({
                    "name": "delete_layers",
                    "status": "PASS",
                    "message": "Deleted 2 layers successfully"
                })
                print("  ✓ delete_rhino_layers: PASS")
                
            except Exception as e:
                results["failed"] += 1
                results["tests"].append({
                    "name": "delete_layers",
                    "status": "FAIL",
                    "message": str(e)
                })
                print(f"  ✗ delete_rhino_layers: FAIL - {e}")
        
        return results
    
    async def test_metadata_tools(self) -> Dict[str, Any]:
        """Test metadata management tools"""
        print("Testing Metadata Tools...")
        results = {"passed": 0, "failed": 0, "tests": []}
        
        metadata_tests = [
            {
                "tool": "add_rhino_objects_metadata",
                "name": "add_metadata",
                "params": {
                    "object_ids": ["obj1", "obj2"],
                    "name": "Test Objects",
                    "description": "Objects for testing metadata"
                },
                "mock_response": {
                    "status": "success",
                    "objects_updated": ["obj1", "obj2"],
                    "metadata_added": 2
                }
            },
            {
                "tool": "update_rhino_objects_metadata",
                "name": "update_metadata",
                "params": {
                    "object_ids": ["obj1"],
                    "name": "Updated Test Object",
                    "description": "Updated description for testing"
                },
                "mock_response": {
                    "status": "success",
                    "objects_updated": ["obj1"],
                    "metadata_updated": 1
                }
            }
        ]
        
        client = Client(mcp)
        for test in metadata_tests:
            self.mock_connection_manager.send_to_rhino.return_value = test["mock_response"]
            
            async with client:
                try:
                    result = await client.call_tool(test["tool"], {
                        "session_id": self.session_id,
                        **test["params"]
                    })
                    
                    response_data = json.loads(result.content[0].text)
                    assert response_data["status"] == "success"
                    
                    results["passed"] += 1
                    results["tests"].append({
                        "name": test["name"],
                        "status": "PASS",
                        "message": f"Metadata tool {test['tool']} executed successfully"
                    })
                    print(f"  ✓ {test['name']}: PASS")
                    
                except Exception as e:
                    results["failed"] += 1
                    results["tests"].append({
                        "name": test["name"],
                        "status": "FAIL",
                        "message": str(e)
                    })
                    print(f"  ✗ {test['name']}: FAIL - {e}")
        
        return results
    
    async def test_script_execution_tools(self) -> Dict[str, Any]:
        """Test script execution tools"""
        print("Testing Script Execution Tools...")
        results = {"passed": 0, "failed": 0, "tests": []}
        
        # Test successful script execution
        self.mock_connection_manager.send_to_rhino.return_value = {
            "status": "success",
            "result": "Script executed successfully",
            "printed_output": ["Hello from Rhino!", "Created point at origin"],
            "new_objects_count": 1,
            "new_objects": ["script_point_123"]
        }
        
        client = Client(mcp)
        async with client:
            try:
                result = await client.call_tool("execute_rhino_code", {
                    "session_id": self.session_id,
                    "code": """
import rhinoscriptsyntax as rs
print("Hello from Rhino!")
point_id = rs.AddPoint([0, 0, 0])
print("Created point at origin")
"""
                })
                
                response_data = json.loads(result.content[0].text)
                assert response_data["status"] == "success"
                assert response_data["new_objects_count"] == 1
                
                results["passed"] += 1
                results["tests"].append({
                    "name": "execute_script_success",
                    "status": "PASS",
                    "message": "Script executed and created 1 object"
                })
                print("  ✓ execute_rhino_code (success): PASS")
                
            except Exception as e:
                results["failed"] += 1
                results["tests"].append({
                    "name": "execute_script_success",
                    "status": "FAIL",
                    "message": str(e)
                })
                print(f"  ✗ execute_rhino_code (success): FAIL - {e}")
        
        # Test script with error
        self.mock_connection_manager.send_to_rhino.return_value = {
            "status": "error",
            "error": "NameError: name 'undefined_variable' is not defined",
            "printed_output": []
        }
        
        async with client:
            try:
                result = await client.call_tool("execute_rhino_code", {
                    "session_id": self.session_id,
                    "code": "print(undefined_variable)"
                })
                
                response_data = json.loads(result.content[0].text)
                assert response_data["status"] == "error"
                assert "NameError" in response_data["error"]
                
                results["passed"] += 1
                results["tests"].append({
                    "name": "execute_script_error",
                    "status": "PASS",
                    "message": "Script error handled correctly"
                })
                print("  ✓ execute_rhino_code (error handling): PASS")
                
            except Exception as e:
                results["failed"] += 1
                results["tests"].append({
                    "name": "execute_script_error",
                    "status": "FAIL",
                    "message": str(e)
                })
                print(f"  ✗ execute_rhino_code (error handling): FAIL - {e}")
        
        return results
    
    async def test_viewport_tools(self) -> Dict[str, Any]:
        """Test viewport capture tools"""
        print("Testing Viewport Tools...")
        results = {"passed": 0, "failed": 0, "tests": []}
        
        # Test viewport capture
        self.mock_connection_manager.send_to_rhino.return_value = {
            "status": "success",
            "image_path": "/tmp/viewport_123.png",
            "format": "png",
            "width": 1920,
            "height": 1080,
            "file_size": 245760
        }
        
        client = Client(mcp)
        async with client:
            try:
                result = await client.call_tool("capture_rhino_viewport", {
                    "session_id": self.session_id,
                    "width": 1920,
                    "height": 1080,
                    "format": "png"
                })
                
                response_data = json.loads(result.content[0].text)
                assert response_data["status"] == "success"
                assert response_data["format"] == "png"
                assert response_data["width"] == 1920
                
                results["passed"] += 1
                results["tests"].append({
                    "name": "capture_viewport",
                    "status": "PASS",
                    "message": "Viewport captured successfully"
                })
                print("  ✓ capture_rhino_viewport: PASS")
                
            except Exception as e:
                results["failed"] += 1
                results["tests"].append({
                    "name": "capture_viewport",
                    "status": "FAIL",
                    "message": str(e)
                })
                print(f"  ✗ capture_rhino_viewport: FAIL - {e}")
        
        return results
    
    async def test_documentation_tools(self) -> Dict[str, Any]:
        """Test documentation lookup tools"""
        print("Testing Documentation Tools...")
        results = {"passed": 0, "failed": 0, "tests": []}
        
        # Note: This tool doesn't use connection manager
        client = Client(mcp)
        async with client:
            try:
                result = await client.call_tool("look_up_RhinoScriptSyntax", {
                    "function_name": "AddPoint"
                })
                
                # Should return some documentation or error message
                assert len(result.content[0].text) > 0
                
                results["passed"] += 1
                results["tests"].append({
                    "name": "lookup_docs",
                    "status": "PASS",
                    "message": "Documentation lookup completed"
                })
                print("  ✓ look_up_RhinoScriptSyntax: PASS")
                
            except Exception as e:
                results["failed"] += 1
                results["tests"].append({
                    "name": "lookup_docs",
                    "status": "FAIL",
                    "message": str(e)
                })
                print(f"  ✗ look_up_RhinoScriptSyntax: FAIL - {e}")
        
        return results
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all MCP tool tests"""
        print("🧪 Starting Remote MCP Server Tool Testing")
        print("=" * 60)
        
        # Setup mocking
        patcher = self.setup_mock_connection_manager()
        
        try:
            # Run all test suites
            test_suites = [
                ("Scene Information Tools", self.test_scene_info_tools),
                ("Object Creation Tools", self.test_object_creation_tools),
                ("Object Manipulation Tools", self.test_object_manipulation_tools),
                ("Layer Management Tools", self.test_layer_management_tools),
                ("Metadata Tools", self.test_metadata_tools),
                ("Script Execution Tools", self.test_script_execution_tools),
                ("Viewport Tools", self.test_viewport_tools),
                ("Documentation Tools", self.test_documentation_tools),
            ]
            
            all_results = {}
            total_passed = 0
            total_failed = 0
            
            for suite_name, test_func in test_suites:
                print(f"\n--- {suite_name} ---")
                suite_results = await test_func()
                all_results[suite_name] = suite_results
                
                total_passed += suite_results["passed"]
                total_failed += suite_results["failed"]
                
                print(f"Suite Results: {suite_results['passed']} passed, {suite_results['failed']} failed")
            
            # Generate summary report
            print(f"\n{'='*60}")
            print("📊 FINAL RESULTS")
            print(f"{'='*60}")
            
            print(f"Total Tests: {total_passed + total_failed}")
            print(f"✅ Passed: {total_passed}")
            print(f"❌ Failed: {total_failed}")
            print(f"Success Rate: {(total_passed/(total_passed + total_failed)*100):.1f}%")
            
            print(f"\n📋 Suite Breakdown:")
            for suite_name, results in all_results.items():
                total = results["passed"] + results["failed"]
                rate = (results["passed"] / total * 100) if total > 0 else 0
                status = "✅" if results["failed"] == 0 else "❌"
                print(f"  {status} {suite_name}: {results['passed']}/{total} ({rate:.1f}%)")
            
            # Show failed tests
            failed_tests = []
            for suite_results in all_results.values():
                failed_tests.extend([t for t in suite_results["tests"] if t["status"] == "FAIL"])
            
            if failed_tests:
                print(f"\n❌ Failed Tests ({len(failed_tests)}):")
                for test in failed_tests:
                    print(f"  • {test['name']}: {test['message']}")
            
            # Save detailed results
            report_data = {
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total_tests": total_passed + total_failed,
                    "passed": total_passed,
                    "failed": total_failed,
                    "success_rate": (total_passed/(total_passed + total_failed)*100) if (total_passed + total_failed) > 0 else 0
                },
                "suite_results": all_results
            }
            
            report_file = os.path.join(os.path.dirname(__file__), "mcp_test_results.json")
            with open(report_file, 'w') as f:
                json.dump(report_data, f, indent=2)
            
            print(f"\n📄 Detailed results saved to: {report_file}")
            print("=" * 60)
            
            return report_data
            
        finally:
            # Clean up mocking
            patcher.stop()


async def main():
    """Main entry point"""
    print("🚀 Remote MCP Server Tool Testing")
    print("Testing all MCP tools using FastMCP in-memory client")
    print()
    
    runner = MCPTestRunner()
    results = await runner.run_all_tests()
    
    # Exit with appropriate code
    if results["summary"]["failed"] == 0:
        print("\n🎉 All tests passed! MCP tools are working correctly.")
        return 0
    else:
        print(f"\n⚠️  {results['summary']['failed']} tests failed. See details above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main()) 