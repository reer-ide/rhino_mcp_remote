#!/usr/bin/env python3
"""
Comprehensive Tests for All MCP Tools in Remote Rhino MCP Server
Tests all available MCP tools using FastMCP's in-memory testing capabilities.
"""

import pytest
from fastmcp import Client
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
from datetime import datetime
import json
from typing import Dict, Any

from remote_server.server import mcp


@pytest.fixture
def mock_connection_manager():
    """Mock the connection manager for testing"""
    with patch('remote_server.server.connection_manager') as mock_cm:
        # Setup session management mocks
        mock_session = MagicMock()
        mock_session.session_id = "test-session-123"
        mock_session.user_id = "test-user"
        mock_session.status = "active"
        mock_session.instance_id = "test-instance-456"
        
        mock_cm.get_session = AsyncMock(return_value=mock_session)
        mock_cm.send_to_rhino = AsyncMock()
        
        yield mock_cm


@pytest.fixture  
def test_session_id():
    """Provide a test session ID"""
    return "test-session-123"


class TestSceneInformationTools:
    """Test scene information retrieval tools"""

    @pytest.mark.asyncio
    async def test_get_rhino_scene_info(self, mock_connection_manager, test_session_id):
        """Test get_rhino_scene_info tool"""
        # Mock Rhino response
        mock_scene_data = {
            "name": "test_scene.3dm",
            "total_objects": 15,
            "total_layers": 3,
            "layers": [
                {
                    "full_path": "Default",
                    "object_count": 10,
                    "is_visible": True,
                    "is_locked": False,
                    "example_objects": [
                        {"id": "obj1", "name": "Test Object 1", "type": "Point"},
                        {"id": "obj2", "name": "Test Object 2", "type": "Curve"}
                    ]
                }
            ]
        }
        
        mock_connection_manager.send_to_rhino.return_value = mock_scene_data
        
        client = Client(mcp)
        async with client:
            result = await client.call_tool("get_rhino_scene_info", {
                "session_id": test_session_id
            })
            
            assert result.content[0].type == "text"
            response_data = json.loads(result.content[0].text)
            assert response_data["name"] == "test_scene.3dm"
            assert response_data["total_objects"] == 15
            assert len(response_data["layers"]) == 1
            
            # Verify connection manager was called correctly
            mock_connection_manager.send_to_rhino.assert_called_once_with(
                test_session_id, "get_rhino_scene_info", {}
            )

    @pytest.mark.asyncio
    async def test_get_rhino_objects_info_with_filters(self, mock_connection_manager, test_session_id):
        """Test get_rhino_objects_info with various filters"""
        mock_objects_data = {
            "objects": [
                {
                    "id": "obj1",
                    "name": "Test Point",
                    "type": "Point",
                    "layer": "Default",
                    "visible": True,
                    "selected": False,
                    "metadata": {"description": "Test point object"}
                }
            ],
            "total_count": 1
        }
        
        mock_connection_manager.send_to_rhino.return_value = mock_objects_data
        
        client = Client(mcp)
        async with client:
            # Test with object type filter
            result = await client.call_tool("get_rhino_objects_info", {
                "session_id": test_session_id,
                "object_type": "Point",
                "with_metadata": True
            })
            
            assert result.content[0].type == "text"
            response_data = json.loads(result.content[0].text)
            assert len(response_data["objects"]) == 1
            assert response_data["objects"][0]["type"] == "Point"
            assert "metadata" in response_data["objects"][0]

    @pytest.mark.asyncio
    async def test_get_rhino_selected_objects(self, mock_connection_manager, test_session_id):
        """Test get_rhino_selected_objects tool"""
        mock_selected_data = {
            "selected_objects": [
                {
                    "id": "selected1",
                    "name": "Selected Object 1", 
                    "type": "Curve",
                    "layer": "Layer01"
                }
            ],
            "count": 1
        }
        
        mock_connection_manager.send_to_rhino.return_value = mock_selected_data
        
        client = Client(mcp)
        async with client:
            result = await client.call_tool("get_rhino_selected_objects", {
                "session_id": test_session_id
            })
            
            assert result.content[0].type == "text" 
            response_data = json.loads(result.content[0].text)
            assert response_data["count"] == 1
            assert len(response_data["selected_objects"]) == 1


class TestObjectCreationTools:
    """Test object creation tools"""

    @pytest.mark.asyncio
    async def test_create_rhino_basic_geometries_point(self, mock_connection_manager, test_session_id):
        """Test creating a point geometry"""
        mock_creation_result = {
            "status": "success",
            "object_ids": ["new_point_123"],
            "objects_created": 1
        }
        
        mock_connection_manager.send_to_rhino.return_value = mock_creation_result
        
        client = Client(mcp)
        async with client:
            result = await client.call_tool("create_rhino_basic_objects", {
                "session_id": test_session_id,
                "geometry_type": "point",
                "point": {"x": 0, "y": 0, "z": 0},
                "name": "Test Point",
                "description": "A test point created by automation"
            })
            
            assert result.content[0].type == "text"
            response_data = json.loads(result.content[0].text)
            assert response_data["status"] == "success"
            assert len(response_data["object_ids"]) == 1
            assert response_data["objects_created"] == 1

    @pytest.mark.asyncio
    async def test_create_rhino_basic_geometries_sphere(self, mock_connection_manager, test_session_id):
        """Test creating a sphere geometry"""
        mock_creation_result = {
            "status": "success", 
            "object_ids": ["new_sphere_456"],
            "objects_created": 1
        }
        
        mock_connection_manager.send_to_rhino.return_value = mock_creation_result
        
        client = Client(mcp)
        async with client:
            result = await client.call_tool("create_rhino_basic_objects", {
                "session_id": test_session_id,
                "geometry_type": "sphere",
                "center": {"x": 5, "y": 5, "z": 5},
                "radius": 3,
                "name": "Test Sphere"
            })
            
            assert result.content[0].type == "text"
            response_data = json.loads(result.content[0].text)
            assert response_data["status"] == "success"
            assert len(response_data["object_ids"]) == 1

    @pytest.mark.asyncio
    async def test_create_rhino_basic_geometries_batch(self, mock_connection_manager, test_session_id):
        """Test creating multiple geometries in batch"""
        mock_creation_result = {
            "status": "success",
            "object_ids": ["obj1", "obj2", "obj3"], 
            "objects_created": 3
        }
        
        mock_connection_manager.send_to_rhino.return_value = mock_creation_result
        
        client = Client(mcp)
        async with client:
            result = await client.call_tool("create_rhino_basic_objects", {
                "session_id": test_session_id,
                "objects": [
                    {
                        "geometry_type": "point",
                        "point": {"x": 0, "y": 0, "z": 0},
                        "name": "Point 1"
                    },
                    {
                        "geometry_type": "point", 
                        "point": {"x": 1, "y": 1, "z": 0},
                        "name": "Point 2"
                    },
                    {
                        "geometry_type": "line",
                        "start_point": {"x": 0, "y": 0, "z": 0},
                        "end_point": {"x": 1, "y": 1, "z": 0},
                        "name": "Connecting Line"
                    }
                ]
            })
            
            assert result.content[0].type == "text"
            response_data = json.loads(result.content[0].text)
            assert response_data["status"] == "success"
            assert len(response_data["object_ids"]) == 3
            assert response_data["objects_created"] == 3


class TestObjectManipulationTools:
    """Test object manipulation tools"""

    @pytest.mark.asyncio
    async def test_select_rhino_objects_by_ids(self, mock_connection_manager, test_session_id):
        """Test selecting objects by IDs"""
        mock_selection_result = {
            "status": "success",
            "selected_count": 2,
            "selected_objects": ["obj1", "obj2"]
        }
        
        mock_connection_manager.send_to_rhino.return_value = mock_selection_result
        
        client = Client(mcp)
        async with client:
            result = await client.call_tool("select_rhino_objects", {
                "session_id": test_session_id,
                "object_ids": ["obj1", "obj2"]
            })
            
            assert result.content[0].type == "text"
            response_data = json.loads(result.content[0].text)
            assert response_data["status"] == "success"
            assert response_data["selected_count"] == 2

    @pytest.mark.asyncio
    async def test_modify_rhino_objects_translate(self, mock_connection_manager, test_session_id):
        """Test translating objects"""
        mock_modify_result = {
            "status": "success",
            "modified_objects": ["obj1"],
            "modification_count": 1
        }
        
        mock_connection_manager.send_to_rhino.return_value = mock_modify_result
        
        client = Client(mcp)
        async with client:
            result = await client.call_tool("modify_rhino_objects", {
                "session_id": test_session_id,
                "object_ids": ["obj1"],
                "transformation": {
                    "type": "translate",
                    "vector": {"x": 10, "y": 5, "z": 0}
                }
            })
            
            assert result.content[0].type == "text"
            response_data = json.loads(result.content[0].text)
            assert response_data["status"] == "success"
            assert response_data["modification_count"] == 1

    @pytest.mark.asyncio
    async def test_modify_rhino_objects_scale(self, mock_connection_manager, test_session_id):
        """Test scaling objects"""
        mock_modify_result = {
            "status": "success",
            "modified_objects": ["obj1"],
            "modification_count": 1
        }
        
        mock_connection_manager.send_to_rhino.return_value = mock_modify_result
        
        client = Client(mcp)
        async with client:
            result = await client.call_tool("modify_rhino_objects", {
                "session_id": test_session_id,
                "object_ids": ["obj1"],
                "transformation": {
                    "type": "scale",
                    "scale_factor": 2.0,
                    "center": {"x": 0, "y": 0, "z": 0}
                }
            })
            
            assert result.content[0].type == "text"
            response_data = json.loads(result.content[0].text)
            assert response_data["status"] == "success"

    @pytest.mark.asyncio
    async def test_delete_rhino_objects(self, mock_connection_manager, test_session_id):
        """Test deleting objects"""
        mock_delete_result = {
            "status": "success",
            "deleted_objects": ["obj1", "obj2"],
            "deletion_count": 2
        }
        
        mock_connection_manager.send_to_rhino.return_value = mock_delete_result
        
        client = Client(mcp)
        async with client:
            result = await client.call_tool("delete_rhino_objects", {
                "session_id": test_session_id,
                "object_ids": ["obj1", "obj2"]
            })
            
            assert result.content[0].type == "text"
            response_data = json.loads(result.content[0].text)
            assert response_data["status"] == "success"
            assert response_data["deletion_count"] == 2


class TestLayerManagementTools:
    """Test layer management tools"""

    @pytest.mark.asyncio
    async def test_create_rhino_layers(self, mock_connection_manager, test_session_id):
        """Test creating layers"""
        mock_layer_result = {
            "status": "success",
            "created_layers": ["Layer01", "Layer02"],
            "layers_created": 2
        }
        
        mock_connection_manager.send_to_rhino.return_value = mock_layer_result
        
        client = Client(mcp)
        async with client:
            result = await client.call_tool("create_rhino_layers", {
                "session_id": test_session_id,
                "layers": [
                    {
                        "name": "Layer01",
                        "color": {"r": 255, "g": 0, "b": 0},
                        "is_visible": True
                    },
                    {
                        "name": "Layer02", 
                        "color": {"r": 0, "g": 255, "b": 0},
                        "is_visible": False
                    }
                ]
            })
            
            assert result.content[0].type == "text"
            response_data = json.loads(result.content[0].text)
            assert response_data["status"] == "success"
            assert response_data["layers_created"] == 2

    @pytest.mark.asyncio
    async def test_delete_rhino_layers(self, mock_connection_manager, test_session_id):
        """Test deleting layers"""
        mock_delete_result = {
            "status": "success",
            "deleted_layers": ["Layer01", "Layer02"],
            "layers_deleted": 2
        }
        
        mock_connection_manager.send_to_rhino.return_value = mock_delete_result
        
        client = Client(mcp)
        async with client:
            result = await client.call_tool("delete_rhino_layers", {
                "session_id": test_session_id,
                "layer_names": ["Layer01", "Layer02"]
            })
            
            assert result.content[0].type == "text"
            response_data = json.loads(result.content[0].text)
            assert response_data["status"] == "success"
            assert response_data["layers_deleted"] == 2


class TestMetadataTools:
    """Test metadata management tools"""

    @pytest.mark.asyncio
    async def test_add_rhino_objects_metadata(self, mock_connection_manager, test_session_id):
        """Test adding metadata to objects"""
        mock_metadata_result = {
            "status": "success",
            "objects_updated": ["obj1", "obj2"],
            "metadata_added": 2
        }
        
        mock_connection_manager.send_to_rhino.return_value = mock_metadata_result
        
        client = Client(mcp)
        async with client:
            result = await client.call_tool("add_rhino_objects_metadata", {
                "session_id": test_session_id,
                "object_ids": ["obj1", "obj2"],
                "name": "Test Objects",
                "description": "Objects created during testing"
            })
            
            assert result.content[0].type == "text"
            response_data = json.loads(result.content[0].text)
            assert response_data["status"] == "success"
            assert response_data["metadata_added"] == 2

    @pytest.mark.asyncio
    async def test_update_rhino_objects_metadata(self, mock_connection_manager, test_session_id):
        """Test updating existing metadata"""
        mock_update_result = {
            "status": "success",
            "objects_updated": ["obj1"],
            "metadata_updated": 1
        }
        
        mock_connection_manager.send_to_rhino.return_value = mock_update_result
        
        client = Client(mcp)
        async with client:
            result = await client.call_tool("update_rhino_objects_metadata", {
                "session_id": test_session_id,
                "object_ids": ["obj1"],
                "name": "Updated Test Object",
                "description": "This object metadata was updated"
            })
            
            assert result.content[0].type == "text"
            response_data = json.loads(result.content[0].text)
            assert response_data["status"] == "success"
            assert response_data["metadata_updated"] == 1


class TestScriptExecutionTools:
    """Test script execution tools"""

    @pytest.mark.asyncio
    async def test_execute_rhino_code_simple(self, mock_connection_manager, test_session_id):
        """Test executing simple Python code"""
        mock_execution_result = {
            "status": "success",
            "result": "Code executed successfully",
            "printed_output": ["Hello from Rhino!", "Point created at (0,0,0)"],
            "new_objects_count": 1,
            "new_objects": ["new_point_789"]
        }
        
        mock_connection_manager.send_to_rhino.return_value = mock_execution_result
        
        client = Client(mcp)
        async with client:
            result = await client.call_tool("execute_rhino_code", {
                "session_id": test_session_id,
                "code": """
import rhinoscriptsyntax as rs
print("Hello from Rhino!")
point_id = rs.AddPoint([0, 0, 0])
print(f"Point created at (0,0,0)")
"""
            })
            
            assert result.content[0].type == "text"
            response_data = json.loads(result.content[0].text)
            assert response_data["status"] == "success"
            assert len(response_data["printed_output"]) == 2
            assert response_data["new_objects_count"] == 1

    @pytest.mark.asyncio
    async def test_execute_rhino_code_with_error(self, mock_connection_manager, test_session_id):
        """Test script execution with error handling"""
        mock_execution_result = {
            "status": "error",
            "error": "NameError: name 'undefined_variable' is not defined",
            "printed_output": []
        }
        
        mock_connection_manager.send_to_rhino.return_value = mock_execution_result
        
        client = Client(mcp)
        async with client:
            result = await client.call_tool("execute_rhino_code", {
                "session_id": test_session_id,
                "code": "print(undefined_variable)"
            })
            
            assert result.content[0].type == "text"
            response_data = json.loads(result.content[0].text)
            assert response_data["status"] == "error"
            assert "NameError" in response_data["error"]


class TestViewportTools:
    """Test viewport capture tools"""

    @pytest.mark.asyncio
    async def test_capture_rhino_viewport_png(self, mock_connection_manager, test_session_id):
        """Test capturing viewport as PNG"""
        mock_capture_result = {
            "status": "success",
            "image_path": "/tmp/viewport_capture_123.png",
            "format": "png",
            "width": 1920,
            "height": 1080,
            "file_size": 245760
        }
        
        mock_connection_manager.send_to_rhino.return_value = mock_capture_result
        
        client = Client(mcp)
        async with client:
            result = await client.call_tool("capture_rhino_viewport", {
                "session_id": test_session_id,
                "width": 1920,
                "height": 1080,
                "format": "png"
            })
            
            assert result.content[0].type == "text"
            response_data = json.loads(result.content[0].text)
            assert response_data["status"] == "success"
            assert response_data["format"] == "png"
            assert response_data["width"] == 1920
            assert response_data["height"] == 1080

    @pytest.mark.asyncio
    async def test_capture_rhino_viewport_jpg(self, mock_connection_manager, test_session_id):
        """Test capturing viewport as JPG"""
        mock_capture_result = {
            "status": "success",
            "image_path": "/tmp/viewport_capture_456.jpg", 
            "format": "jpg",
            "width": 1024,
            "height": 768,
            "quality": 85,
            "file_size": 156432
        }
        
        mock_connection_manager.send_to_rhino.return_value = mock_capture_result
        
        client = Client(mcp)
        async with client:
            result = await client.call_tool("capture_rhino_viewport", {
                "session_id": test_session_id,
                "width": 1024,
                "height": 768,
                "format": "jpg",
                "quality": 85
            })
            
            assert result.content[0].type == "text"
            response_data = json.loads(result.content[0].text)
            assert response_data["status"] == "success"
            assert response_data["format"] == "jpg"
            assert response_data["quality"] == 85


class TestDocumentationTools:
    """Test documentation and lookup tools"""

    @pytest.mark.asyncio
    async def test_look_up_rhinoscriptsyntax(self, mock_connection_manager, test_session_id):
        """Test RhinoScriptSyntax documentation lookup"""
        # This tool doesn't require connection manager since it queries external docs
        client = Client(mcp)
        async with client:
            result = await client.call_tool("look_up_RhinoScriptSyntax", {
                "function_name": "AddPoint"
            })
            
            assert result.content[0].type == "text"
            # Should contain either documentation or an error message
            assert len(result.content[0].text) > 0


class TestErrorHandling:
    """Test error handling scenarios"""

    @pytest.mark.asyncio
    async def test_invalid_session_id(self, mock_connection_manager):
        """Test behavior with invalid session ID"""
        mock_connection_manager.get_session.return_value = None
        
        client = Client(mcp)
        async with client:
            result = await client.call_tool("get_rhino_scene_info", {
                "session_id": "invalid-session-id"
            })
            
            assert result.content[0].type == "text"
            response_data = json.loads(result.content[0].text)
            assert "error" in response_data or "No active connection" in response_data.get("message", "")

    @pytest.mark.asyncio
    async def test_missing_session_id(self, mock_connection_manager):
        """Test behavior with missing session ID"""
        client = Client(mcp)
        async with client:
            result = await client.call_tool("get_rhino_scene_info", {})
            
            assert result.content[0].type == "text"
            response_data = json.loads(result.content[0].text)
            assert "error" in response_data

    @pytest.mark.asyncio
    async def test_connection_manager_failure(self, mock_connection_manager, test_session_id):
        """Test behavior when connection manager fails"""
        mock_connection_manager.send_to_rhino.side_effect = Exception("Connection failed")
        
        client = Client(mcp)
        async with client:
            result = await client.call_tool("get_rhino_scene_info", {
                "session_id": test_session_id
            })
            
            assert result.content[0].type == "text"
            response_data = json.loads(result.content[0].text)
            assert "error" in response_data


class TestToolIntegration:
    """Test integration workflows using multiple tools"""

    @pytest.mark.asyncio
    async def test_complete_workflow(self, mock_connection_manager, test_session_id):
        """Test a complete workflow using multiple tools"""
        # Setup mocks for each step
        mock_connection_manager.send_to_rhino.side_effect = [
            # Step 1: Create objects
            {
                "status": "success",
                "object_ids": ["obj1", "obj2"],
                "objects_created": 2
            },
            # Step 2: Add metadata
            {
                "status": "success", 
                "objects_updated": ["obj1", "obj2"],
                "metadata_added": 2
            },
            # Step 3: Modify objects
            {
                "status": "success",
                "modified_objects": ["obj1", "obj2"],
                "modification_count": 2
            },
            # Step 4: Query scene
            {
                "name": "test_scene.3dm",
                "total_objects": 12,
                "layers": [{"full_path": "Default", "object_count": 12}]
            }
        ]
        
        client = Client(mcp)
        async with client:
            # Step 1: Create some objects
            create_result = await client.call_tool("create_rhino_basic_objects", {
                "session_id": test_session_id,
                "objects": [
                    {
                        "geometry_type": "point",
                        "point": {"x": 0, "y": 0, "z": 0},
                        "name": "Workflow Point 1"
                    },
                    {
                        "geometry_type": "point", 
                        "point": {"x": 5, "y": 5, "z": 0},
                        "name": "Workflow Point 2"
                    }
                ]
            })
            
            create_data = json.loads(create_result.content[0].text)
            assert create_data["status"] == "success"
            created_ids = create_data["object_ids"]
            
            # Step 2: Add metadata to created objects
            metadata_result = await client.call_tool("add_rhino_objects_metadata", {
                "session_id": test_session_id,
                "object_ids": created_ids,
                "name": "Workflow Objects",
                "description": "Objects created during workflow test"
            })
            
            metadata_data = json.loads(metadata_result.content[0].text)
            assert metadata_data["status"] == "success"
            
            # Step 3: Modify the objects
            modify_result = await client.call_tool("modify_rhino_objects", {
                "session_id": test_session_id,
                "object_ids": created_ids,
                "transformation": {
                    "type": "translate",
                    "vector": {"x": 10, "y": 0, "z": 5}
                }
            })
            
            modify_data = json.loads(modify_result.content[0].text)
            assert modify_data["status"] == "success"
            
            # Step 4: Query the final scene
            scene_result = await client.call_tool("get_rhino_scene_info", {
                "session_id": test_session_id
            })
            
            scene_data = json.loads(scene_result.content[0].text)
            assert scene_data["total_objects"] == 12
            
            # Verify all calls were made
            assert mock_connection_manager.send_to_rhino.call_count == 4


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"]) 