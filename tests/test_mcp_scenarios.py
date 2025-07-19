#!/usr/bin/env python3
"""
Scenario-Based Tests for MCP Tools
Tests realistic workflows that combine multiple MCP tools together.
"""

import pytest
from fastmcp import Client
from unittest.mock import patch, MagicMock, AsyncMock
import json
from datetime import datetime

from remote_server.server import mcp


@pytest.fixture
def mock_connection_manager():
    """Mock the connection manager for scenario testing"""
    with patch('remote_server.server.connection_manager') as mock_cm:
        mock_session = MagicMock()
        mock_session.session_id = "scenario-test-session"
        mock_session.user_id = "scenario-user"
        mock_session.status = "active"
        
        mock_cm.get_session = AsyncMock(return_value=mock_session)
        mock_cm.send_to_rhino = AsyncMock()
        
        yield mock_cm


@pytest.fixture
def test_session_id():
    """Provide test session ID for scenarios"""
    return "scenario-test-session"


class TestParametricDesignWorkflow:
    """Test parametric design workflow scenario"""

    @pytest.mark.asyncio
    async def test_parametric_grid_creation(self, mock_connection_manager, test_session_id):
        """Test creating a parametric grid using script execution and object creation"""
        
        # Mock responses for each step of the workflow
        mock_responses = [
            # Step 1: Execute script to create grid points
            {
                "status": "success",
                "result": "Grid points created successfully",
                "printed_output": ["Created 25 grid points (5x5)"],
                "new_objects_count": 25,
                "new_objects": [f"grid_point_{i}" for i in range(25)]
            },
            # Step 2: Add metadata to grid points
            {
                "status": "success",
                "objects_updated": [f"grid_point_{i}" for i in range(25)],
                "metadata_added": 25
            },
            # Step 3: Create connecting lines
            {
                "status": "success",
                "object_ids": [f"line_{i}" for i in range(20)],
                "objects_created": 20
            },
            # Step 4: Query final scene
            {
                "name": "parametric_design.3dm",
                "total_objects": 45,
                "layers": [
                    {
                        "full_path": "Grid_Points",
                        "object_count": 25,
                        "is_visible": True
                    },
                    {
                        "full_path": "Connecting_Lines", 
                        "object_count": 20,
                        "is_visible": True
                    }
                ]
            }
        ]
        
        mock_connection_manager.send_to_rhino.side_effect = mock_responses
        
        client = Client(mcp)
        async with client:
            # Step 1: Create parametric grid using script
            grid_script = """
import rhinoscriptsyntax as rs

# Create 5x5 grid of points
points = []
for x in range(5):
    for y in range(5):
        point_id = rs.AddPoint([x * 10, y * 10, 0])
        points.append(point_id)

print(f"Created {len(points)} grid points (5x5)")
"""
            
            script_result = await client.call_tool("execute_rhino_code", {
                "session_id": test_session_id,
                "code": grid_script
            })
            
            script_data = json.loads(script_result.content[0].text)
            assert script_data["status"] == "success"
            assert script_data["new_objects_count"] == 25
            grid_points = script_data["new_objects"]
            
            # Step 2: Add metadata to all grid points
            metadata_result = await client.call_tool("add_rhino_objects_metadata", {
                "session_id": test_session_id,
                "object_ids": grid_points,
                "name": "Parametric Grid Point",
                "description": "Grid point created by parametric design workflow"
            })
            
            metadata_data = json.loads(metadata_result.content[0].text)
            assert metadata_data["status"] == "success"
            assert metadata_data["metadata_added"] == 25
            
            # Step 3: Create connecting lines between points
            lines_result = await client.call_tool("create_rhino_basic_objects", {
                "session_id": test_session_id,
                "objects": [
                    {
                        "geometry_type": "line",
                        "start_point": {"x": i * 10, "y": 0, "z": 0},
                        "end_point": {"x": i * 10, "y": 40, "z": 0},
                        "name": f"Grid Line {i}",
                        "layer": "Connecting_Lines"
                    } for i in range(5)
                ] + [
                    {
                        "geometry_type": "line", 
                        "start_point": {"x": 0, "y": j * 10, "z": 0},
                        "end_point": {"x": 40, "y": j * 10, "z": 0},
                        "name": f"Grid Line {j+5}",
                        "layer": "Connecting_Lines"
                    } for j in range(5)
                ]
            })
            
            lines_data = json.loads(lines_result.content[0].text)
            assert lines_data["status"] == "success"
            assert lines_data["objects_created"] == 20
            
            # Step 4: Analyze final parametric design
            scene_result = await client.call_tool("get_rhino_scene_info", {
                "session_id": test_session_id
            })
            
            scene_data = json.loads(scene_result.content[0].text)
            assert scene_data["total_objects"] == 45  # 25 points + 20 lines
            assert len(scene_data["layers"]) == 2
            
            # Verify all operations were called
            assert mock_connection_manager.send_to_rhino.call_count == 4


class TestArchitecturalModelingWorkflow:
    """Test architectural modeling workflow scenario"""

    @pytest.mark.asyncio
    async def test_building_design_workflow(self, mock_connection_manager, test_session_id):
        """Test complete building design workflow with layers and components"""
        
        mock_responses = [
            # Step 1: Create architectural layers
            {
                "status": "success",
                "created_layers": ["Foundation", "Walls", "Floors", "Roof", "Windows"],
                "layers_created": 5
            },
            # Step 2: Create foundation
            {
                "status": "success",
                "object_ids": ["foundation_slab"],
                "objects_created": 1
            },
            # Step 3: Create walls via script
            {
                "status": "success",
                "result": "Building walls created",
                "printed_output": ["Created 4 exterior walls", "All walls assigned to Walls layer"],
                "new_objects_count": 4,
                "new_objects": ["wall_north", "wall_south", "wall_east", "wall_west"]
            },
            # Step 4: Create floor
            {
                "status": "success", 
                "object_ids": ["main_floor"],
                "objects_created": 1
            },
            # Step 5: Create roof
            {
                "status": "success",
                "object_ids": ["main_roof"],
                "objects_created": 1
            },
            # Step 6: Add windows
            {
                "status": "success",
                "object_ids": ["window_1", "window_2", "window_3"],
                "objects_created": 3
            },
            # Step 7: Add metadata to building components
            {
                "status": "success",
                "objects_updated": ["foundation_slab"],
                "metadata_added": 1
            },
            {
                "status": "success",
                "objects_updated": ["wall_north", "wall_south", "wall_east", "wall_west"],
                "metadata_added": 4
            },
            # Step 8: Final building analysis
            {
                "objects": [
                    {
                        "id": "foundation_slab",
                        "name": "Building Foundation",
                        "type": "Brep",
                        "layer": "Foundation",
                        "metadata": {"description": "Main structural foundation"}
                    },
                    {
                        "id": "wall_north",
                        "name": "North Wall",
                        "type": "Brep", 
                        "layer": "Walls",
                        "metadata": {"description": "North exterior wall"}
                    }
                ],
                "total_count": 10
            }
        ]
        
        mock_connection_manager.send_to_rhino.side_effect = mock_responses
        
        client = Client(mcp)
        async with client:
            # Step 1: Create architectural layers
            layers_result = await client.call_tool("create_rhino_layers", {
                "session_id": test_session_id,
                "layers": [
                    {"name": "Foundation", "color": {"r": 139, "g": 69, "b": 19}, "is_visible": True},
                    {"name": "Walls", "color": {"r": 169, "g": 169, "b": 169}, "is_visible": True},
                    {"name": "Floors", "color": {"r": 222, "g": 184, "b": 135}, "is_visible": True},
                    {"name": "Roof", "color": {"r": 139, "g": 0, "b": 0}, "is_visible": True},
                    {"name": "Windows", "color": {"r": 173, "g": 216, "b": 230}, "is_visible": True}
                ]
            })
            
            layers_data = json.loads(layers_result.content[0].text)
            assert layers_data["status"] == "success"
            assert layers_data["layers_created"] == 5
            
            # Step 2: Create foundation slab
            foundation_result = await client.call_tool("create_rhino_basic_objects", {
                "session_id": test_session_id,
                "geometry_type": "box",
                "corner1": {"x": 0, "y": 0, "z": -1},
                "corner2": {"x": 20, "y": 15, "z": 0},
                "layer": "Foundation",
                "name": "Building Foundation"
            })
            
            foundation_data = json.loads(foundation_result.content[0].text)
            assert foundation_data["status"] == "success"
            foundation_id = foundation_data["object_ids"][0]
            
            # Step 3: Create walls using script for precision
            walls_script = """
import rhinoscriptsyntax as rs

# Create building walls
walls = []

# North wall (front)
north_wall = rs.AddBox([(0, 0, 0), (20, 0.3, 3), (20, 0, 3), (0, 0.3, 3), 
                       (0, 0, 0), (20, 0, 0), (20, 0.3, 0), (0, 0.3, 0)])
if north_wall:
    rs.ObjectLayer(north_wall, "Walls")
    rs.ObjectName(north_wall, "North Wall")
    walls.append(north_wall)

# South wall (back)  
south_wall = rs.AddBox([(0, 15, 0), (20, 15.3, 3), (20, 15, 3), (0, 15.3, 3),
                       (0, 15, 0), (20, 15, 0), (20, 15.3, 0), (0, 15.3, 0)])
if south_wall:
    rs.ObjectLayer(south_wall, "Walls")
    rs.ObjectName(south_wall, "South Wall")
    walls.append(south_wall)

# East and West walls...
print(f"Created {len(walls)} exterior walls")
print("All walls assigned to Walls layer")
"""
            
            walls_result = await client.call_tool("execute_rhino_code", {
                "session_id": test_session_id,
                "code": walls_script
            })
            
            walls_data = json.loads(walls_result.content[0].text)
            assert walls_data["status"] == "success"
            assert walls_data["new_objects_count"] == 4
            wall_ids = walls_data["new_objects"]
            
            # Step 4: Create main floor
            floor_result = await client.call_tool("create_rhino_basic_objects", {
                "session_id": test_session_id,
                "geometry_type": "box",
                "corner1": {"x": 0.3, "y": 0.3, "z": 0},
                "corner2": {"x": 19.7, "y": 14.7, "z": 0.2},
                "layer": "Floors",
                "name": "Main Floor"
            })
            
            floor_data = json.loads(floor_result.content[0].text)
            assert floor_data["status"] == "success"
            
            # Step 5: Create roof
            roof_result = await client.call_tool("create_rhino_basic_objects", {
                "session_id": test_session_id,
                "geometry_type": "box",
                "corner1": {"x": -0.5, "y": -0.5, "z": 3},
                "corner2": {"x": 20.5, "y": 15.5, "z": 3.3},
                "layer": "Roof",
                "name": "Main Roof"
            })
            
            roof_data = json.loads(roof_result.content[0].text)
            assert roof_data["status"] == "success"
            
            # Step 6: Add windows
            windows_result = await client.call_tool("create_rhino_basic_objects", {
                "session_id": test_session_id,
                "objects": [
                    {
                        "geometry_type": "box",
                        "corner1": {"x": 3, "y": -0.1, "z": 1},
                        "corner2": {"x": 5, "y": 0.4, "z": 2.5},
                        "layer": "Windows",
                        "name": "Front Window 1"
                    },
                    {
                        "geometry_type": "box",
                        "corner1": {"x": 8, "y": -0.1, "z": 1},
                        "corner2": {"x": 10, "y": 0.4, "z": 2.5},
                        "layer": "Windows", 
                        "name": "Front Window 2"
                    },
                    {
                        "geometry_type": "box",
                        "corner1": {"x": 13, "y": -0.1, "z": 1},
                        "corner2": {"x": 15, "y": 0.4, "z": 2.5},
                        "layer": "Windows",
                        "name": "Front Window 3"
                    }
                ]
            })
            
            windows_data = json.loads(windows_result.content[0].text)
            assert windows_data["status"] == "success"
            assert windows_data["objects_created"] == 3
            
            # Step 7: Add detailed metadata to components
            foundation_meta_result = await client.call_tool("add_rhino_objects_metadata", {
                "session_id": test_session_id,
                "object_ids": [foundation_id],
                "name": "Building Foundation",
                "description": "Main structural foundation slab - reinforced concrete"
            })
            
            foundation_meta_data = json.loads(foundation_meta_result.content[0].text)
            assert foundation_meta_data["status"] == "success"
            
            walls_meta_result = await client.call_tool("add_rhino_objects_metadata", {
                "session_id": test_session_id,
                "object_ids": wall_ids,
                "name": "Exterior Wall",
                "description": "Load-bearing exterior wall - 8 inch concrete block"
            })
            
            walls_meta_data = json.loads(walls_meta_result.content[0].text)
            assert walls_meta_data["status"] == "success"
            assert walls_meta_data["metadata_added"] == 4
            
            # Step 8: Analyze complete building
            building_analysis = await client.call_tool("get_rhino_objects_info", {
                "session_id": test_session_id,
                "with_metadata": True
            })
            
            analysis_data = json.loads(building_analysis.content[0].text)
            assert analysis_data["total_count"] == 10  # Foundation + 4 walls + floor + roof + 3 windows
            assert len([obj for obj in analysis_data["objects"] if "metadata" in obj]) >= 5
            
            # Verify all calls were made
            assert mock_connection_manager.send_to_rhino.call_count == 9


class TestDesignIterationWorkflow:
    """Test design iteration and version control workflow"""

    @pytest.mark.asyncio
    async def test_design_evolution_workflow(self, mock_connection_manager, test_session_id):
        """Test iterative design process with version tracking"""
        
        mock_responses = [
            # Initial design creation
            {
                "status": "success",
                "object_ids": ["design_sphere_v1", "design_base_v1"],
                "objects_created": 2
            },
            # Add v1.0 metadata
            {
                "status": "success",
                "objects_updated": ["design_sphere_v1", "design_base_v1"],
                "metadata_added": 2
            },
            # Scale transformation (v1.1)
            {
                "status": "success",
                "modified_objects": ["design_sphere_v1", "design_base_v1"],
                "modification_count": 2
            },
            # Update metadata to v1.1
            {
                "status": "success",
                "objects_updated": ["design_sphere_v1"],
                "metadata_updated": 1
            },
            # Translation transformation (v1.2)
            {
                "status": "success",
                "modified_objects": ["design_sphere_v1", "design_base_v1"],
                "modification_count": 2
            },
            # Create alternative design (v2.0)
            {
                "status": "success",
                "object_ids": ["design_cylinder_v2"],
                "objects_created": 1
            },
            # Add alternative metadata
            {
                "status": "success",
                "objects_updated": ["design_cylinder_v2"],
                "metadata_added": 1
            },
            # Compare designs query
            {
                "objects": [
                    {
                        "id": "design_sphere_v1",
                        "name": "Design Sphere v1.2",
                        "type": "Sphere",
                        "metadata": {"description": "Scaled and translated version - iteration 2", "version": "1.2"}
                    },
                    {
                        "id": "design_base_v1",
                        "name": "Design Base v1.0", 
                        "type": "Box",
                        "metadata": {"description": "Base component for design", "version": "1.0"}
                    },
                    {
                        "id": "design_cylinder_v2",
                        "name": "Design Alternative v2.0",
                        "type": "Cylinder",
                        "metadata": {"description": "Alternative cylindrical design approach", "version": "2.0"}
                    }
                ],
                "total_count": 3
            }
        ]
        
        mock_connection_manager.send_to_rhino.side_effect = mock_responses
        
        client = Client(mcp)
        async with client:
            # Initial design creation (v1.0)
            initial_result = await client.call_tool("create_rhino_basic_objects", {
                "session_id": test_session_id,
                "objects": [
                    {
                        "geometry_type": "sphere",
                        "center": {"x": 0, "y": 0, "z": 5},
                        "radius": 3,
                        "name": "Design Sphere v1.0"
                    },
                    {
                        "geometry_type": "box",
                        "corner1": {"x": -2, "y": -2, "z": 0},
                        "corner2": {"x": 2, "y": 2, "z": 1},
                        "name": "Design Base v1.0"
                    }
                ]
            })
            
            initial_data = json.loads(initial_result.content[0].text)
            assert initial_data["status"] == "success"
            design_objects = initial_data["object_ids"]
            
            # Add initial metadata
            initial_meta_result = await client.call_tool("add_rhino_objects_metadata", {
                "session_id": test_session_id,
                "object_ids": design_objects,
                "name": "Initial Design v1.0",
                "description": "Initial design concept - baseline for iterations"
            })
            
            initial_meta_data = json.loads(initial_meta_result.content[0].text)
            assert initial_meta_data["status"] == "success"
            
            # First iteration: Scale up (v1.1)
            scale_result = await client.call_tool("modify_rhino_objects", {
                "session_id": test_session_id,
                "object_ids": design_objects,
                "transformation": {
                    "type": "scale",
                    "scale_factor": 1.5,
                    "center": {"x": 0, "y": 0, "z": 2.5}
                }
            })
            
            scale_data = json.loads(scale_result.content[0].text)
            assert scale_data["status"] == "success"
            assert scale_data["modification_count"] == 2
            
            # Update metadata for v1.1
            v11_meta_result = await client.call_tool("update_rhino_objects_metadata", {
                "session_id": test_session_id,
                "object_ids": [design_objects[0]],  # Just the sphere
                "name": "Design Sphere v1.1",
                "description": "Scaled up version - iteration 1"
            })
            
            v11_meta_data = json.loads(v11_meta_result.content[0].text)
            assert v11_meta_data["status"] == "success"
            
            # Second iteration: Translate (v1.2)
            translate_result = await client.call_tool("modify_rhino_objects", {
                "session_id": test_session_id,
                "object_ids": design_objects,
                "transformation": {
                    "type": "translate",
                    "vector": {"x": 10, "y": 5, "z": 0}
                }
            })
            
            translate_data = json.loads(translate_result.content[0].text)
            assert translate_data["status"] == "success"
            
            # Create alternative design (v2.0)
            alternative_result = await client.call_tool("create_rhino_basic_objects", {
                "session_id": test_session_id,
                "geometry_type": "cylinder",
                "center": {"x": 20, "y": 0, "z": 0},
                "radius": 4,
                "height": 8,
                "name": "Design Alternative v2.0"
            })
            
            alternative_data = json.loads(alternative_result.content[0].text)
            assert alternative_data["status"] == "success"
            alternative_id = alternative_data["object_ids"][0]
            
            # Add metadata to alternative
            alt_meta_result = await client.call_tool("add_rhino_objects_metadata", {
                "session_id": test_session_id,
                "object_ids": [alternative_id],
                "name": "Design Alternative v2.0",
                "description": "Alternative cylindrical design approach"
            })
            
            alt_meta_data = json.loads(alt_meta_result.content[0].text)
            assert alt_meta_data["status"] == "success"
            
            # Compare all design versions
            comparison_result = await client.call_tool("get_rhino_objects_info", {
                "session_id": test_session_id,
                "object_name_contains": "Design",
                "with_metadata": True
            })
            
            comparison_data = json.loads(comparison_result.content[0].text)
            assert comparison_data["total_count"] == 3
            
            # Verify version progression
            designs = comparison_data["objects"]
            versions = [obj["metadata"]["version"] for obj in designs if "version" in obj.get("metadata", {})]
            assert len(versions) >= 2  # Should have multiple versions
            
            # Verify all operations were called
            assert mock_connection_manager.send_to_rhino.call_count == 8


class TestBatchOperationsWorkflow:
    """Test large-scale batch operations workflow"""

    @pytest.mark.asyncio
    async def test_large_batch_processing(self, mock_connection_manager, test_session_id):
        """Test processing large batches of objects efficiently"""
        
        # Generate mock data for large batch
        batch_size = 50
        batch_object_ids = [f"batch_obj_{i}" for i in range(batch_size)]
        
        mock_responses = [
            # Create large batch of objects
            {
                "status": "success",
                "object_ids": batch_object_ids,
                "objects_created": batch_size
            },
            # Add metadata to all objects
            {
                "status": "success",
                "objects_updated": batch_object_ids,
                "metadata_added": batch_size
            },
            # Select subset for modification
            {
                "status": "success",
                "selected_count": batch_size // 2,
                "selected_objects": batch_object_ids[:batch_size//2]
            },
            # Transform selected objects
            {
                "status": "success",
                "modified_objects": batch_object_ids[:batch_size//2],
                "modification_count": batch_size // 2
            },
            # Final scene analysis
            {
                "name": "batch_operations.3dm",
                "total_objects": batch_size + 10,  # Original + created
                "layers": [
                    {"full_path": "Batch_Objects", "object_count": batch_size}
                ]
            }
        ]
        
        mock_connection_manager.send_to_rhino.side_effect = mock_responses
        
        client = Client(mcp)
        async with client:
            # Create large batch of points
            batch_objects = [
                {
                    "geometry_type": "point",
                    "point": {"x": i % 10, "y": i // 10, "z": 0},
                    "name": f"Batch Point {i}",
                    "layer": "Batch_Objects"
                } for i in range(batch_size)
            ]
            
            batch_result = await client.call_tool("create_rhino_basic_objects", {
                "session_id": test_session_id,
                "objects": batch_objects
            })
            
            batch_data = json.loads(batch_result.content[0].text)
            assert batch_data["status"] == "success"
            assert batch_data["objects_created"] == batch_size
            created_ids = batch_data["object_ids"]
            
            # Add metadata to entire batch
            meta_result = await client.call_tool("add_rhino_objects_metadata", {
                "session_id": test_session_id,
                "object_ids": created_ids,
                "name": "Batch Processed Object",
                "description": "Object created during batch processing test"
            })
            
            meta_data = json.loads(meta_result.content[0].text)
            assert meta_data["status"] == "success"
            assert meta_data["metadata_added"] == batch_size
            
            # Select subset for further processing
            subset_ids = created_ids[:batch_size//2]
            select_result = await client.call_tool("select_rhino_objects", {
                "session_id": test_session_id,
                "object_ids": subset_ids
            })
            
            select_data = json.loads(select_result.content[0].text)
            assert select_data["status"] == "success"
            assert select_data["selected_count"] == batch_size // 2
            
            # Transform selected subset
            transform_result = await client.call_tool("modify_rhino_objects", {
                "session_id": test_session_id,
                "object_ids": subset_ids,
                "transformation": {
                    "type": "translate",
                    "vector": {"x": 0, "y": 0, "z": 5}
                }
            })
            
            transform_data = json.loads(transform_result.content[0].text)
            assert transform_data["status"] == "success"
            assert transform_data["modification_count"] == batch_size // 2
            
            # Analyze final scene
            scene_result = await client.call_tool("get_rhino_scene_info", {
                "session_id": test_session_id
            })
            
            scene_data = json.loads(scene_result.content[0].text)
            assert scene_data["total_objects"] >= batch_size
            
            # Verify efficient batch processing
            assert mock_connection_manager.send_to_rhino.call_count == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 