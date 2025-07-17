# Remote MCP Server Testing Suite

This directory contains comprehensive tests for all MCP tools in the Remote Rhino MCP Server using FastMCP's built-in testing capabilities.

## Overview

The testing suite uses **FastMCP's in-memory testing** which allows direct testing of MCP tools without requiring actual Rhino connections. This provides:

- **Fast execution** - No network overhead or process spawning
- **Reliable results** - Controlled mock responses from Rhino
- **Comprehensive coverage** - All 13 MCP tools tested with various scenarios
- **Proper session management** - Mock session handling that mirrors production

## Test Files

### Core Test Suites

- **`test_all_mcp_tools.py`** - Comprehensive tests for all 13 individual MCP tools
- **`test_mcp_scenarios.py`** - Realistic workflow scenarios combining multiple tools
- **`test_mcp_runner.py`** - Master test runner with consolidated reporting

### Legacy Tests

- **`test_server.py`** - Original server tests with mocking patterns
- **`test_connection_system.py`** - Connection and session management tests
- **`test_rhino_script.py`** - Rhino script connection testing
- **`rhino_client.py`** - Mock Rhino client for integration testing

## Available MCP Tools Tested

| Tool Name | Description | Test Coverage |
|-----------|-------------|---------------|
| `get_rhino_scene_info` | Get scene information and layer details | ✅ Basic info, layer filtering |
| `get_rhino_objects_info` | Get detailed object information with filters | ✅ All filter types, metadata |
| `get_rhino_selected_objects` | Get currently selected objects | ✅ Selection states |
| `create_rhino_basic_objects` | Create points, lines, spheres, boxes, etc. | ✅ All geometry types, batch creation |
| `select_rhino_objects` | Select objects by ID, type, or layer | ✅ All selection criteria |
| `modify_rhino_objects` | Transform objects (translate, rotate, scale) | ✅ All transformation types |
| `delete_rhino_objects` | Delete objects from document | ✅ Single and batch deletion |
| `create_rhino_layers` | Create layers with properties | ✅ Colors, visibility, properties |
| `delete_rhino_layers` | Delete layers from document | ✅ Validation and cleanup |
| `add_rhino_objects_metadata` | Add name/description to objects | ✅ Single and batch metadata |
| `update_rhino_objects_metadata` | Update existing metadata | ✅ Partial updates |
| `execute_rhino_code` | Execute Python scripts in Rhino | ✅ Success and error scenarios |
| `capture_rhino_viewport` | Capture viewport as image | ✅ Different formats and sizes |

## Quick Start

### Prerequisites

1. **Install dependencies**:
   ```bash
   cd rhino_mcp_remote
   pip install -r requirements.txt
   ```

2. **Ensure FastMCP is available**:
   ```bash
   python -c "from fastmcp import Client; print('FastMCP ready')"
   ```

### Running Tests

#### Option 1: Run All Tests (Recommended)
```bash
cd rhino_mcp_remote/tests
python test_mcp_runner.py
```

#### Option 2: Run Individual Test Suites
```bash
# Run comprehensive tool tests
pytest test_all_mcp_tools.py -v

# Run scenario tests
pytest test_mcp_scenarios.py -v

# Run all tests with pytest
pytest -v
```

#### Option 3: Run Specific Test Classes
```bash
# Test only scene information tools
pytest test_all_mcp_tools.py::TestSceneInformationTools -v

# Test only object creation
pytest test_all_mcp_tools.py::TestObjectCreationTools -v

# Test parametric design workflow
pytest test_mcp_scenarios.py::TestParametricDesignWorkflow -v
```

## Test Architecture

### FastMCP In-Memory Testing

The tests use FastMCP's `Client` class with the server instance directly:

```python
from fastmcp import Client
from remote_server.server import mcp

client = Client(mcp)  # Direct server instance
async with client:
    result = await client.call_tool("get_rhino_scene_info", {
        "session_id": "test-session-123"
    })
```

### Mock Session Management

Tests mock the connection manager to simulate Rhino sessions:

```python
@pytest.fixture
def mock_connection_manager():
    with patch('remote_server.server.connection_manager') as mock_cm:
        mock_session = MagicMock()
        mock_session.session_id = "test-session-123"
        mock_cm.get_session = AsyncMock(return_value=mock_session)
        mock_cm.send_to_rhino = AsyncMock()
        yield mock_cm
```

### Controlled Rhino Responses

Mock responses simulate actual Rhino behavior:

```python
# Mock successful object creation
mock_cm.send_to_rhino.return_value = {
    "status": "success",
    "object_ids": ["sphere_123", "box_456"],
    "objects_created": 2
}
```

## Test Scenarios

### 1. Individual Tool Testing (`test_all_mcp_tools.py`)

Tests each tool individually with:
- **Valid parameters** - Correct usage patterns
- **Various options** - Different parameter combinations  
- **Error handling** - Invalid sessions, missing parameters
- **Response validation** - Correct data structure and content

### 2. Workflow Scenarios (`test_mcp_scenarios.py`)

Tests realistic usage patterns:

#### Parametric Design Workflow
1. Execute script to create grid points
2. Add metadata to all points
3. Create connecting lines between points
4. Analyze final parametric design

#### Architectural Modeling Workflow  
1. Create architectural layers (Foundation, Walls, Floors, etc.)
2. Create foundation slab
3. Create walls using precise script
4. Add floors and roof
5. Add windows
6. Add detailed metadata to components
7. Analyze complete building

#### Design Iteration Workflow
1. Create initial design (v1.0)
2. Add metadata with version info
3. Apply transformations (v1.1, v1.2)
4. Create alternative design (v2.0)
5. Compare all design versions

#### Batch Operations Workflow
1. Create large batch of objects (50+ items)
2. Add metadata to entire batch
3. Select subset for modification
4. Apply transformations to subset
5. Analyze performance and results

### 3. Master Test Runner (`test_mcp_runner.py`)

Provides:
- **Organized execution** of all test suites
- **Consolidated reporting** with success rates
- **JSON output** for detailed analysis
- **Performance timing** for each test suite
- **Summary statistics** across all tests

## Test Reports

### Console Output
Real-time progress with colored output:
```
🧪 Starting Remote MCP Server Tool Testing
============================================================

--- Scene Information Tools ---
  ✓ get_rhino_scene_info: PASS
  ✓ get_rhino_objects_info: PASS
Suite Results: 2 passed, 0 failed

--- Object Creation Tools ---
  ✓ create_point: PASS
  ✓ create_sphere: PASS
  ✓ create_batch: PASS
Suite Results: 3 passed, 0 failed

============================================================
📊 FINAL RESULTS
============================================================
Total Tests: 25
✅ Passed: 25
❌ Failed: 0
Success Rate: 100.0%
```

### JSON Reports
Detailed results saved to `mcp_test_results.json`:
```json
{
  "timestamp": "2024-01-15T10:30:45.123456",
  "summary": {
    "total_tests": 25,
    "passed": 25,
    "failed": 0,
    "success_rate": 100.0
  },
  "suite_results": {
    "Scene Information Tools": {
      "passed": 2,
      "failed": 0,
      "tests": [
        {
          "name": "get_rhino_scene_info",
          "status": "PASS",
          "message": "Scene info retrieved successfully"
        }
      ]
    }
  }
}
```

## Key Differences from Plugin-Side Tests

### 1. **Testing Approach**
- **Plugin tests**: HTTP calls to remote server endpoints
- **Server tests**: Direct FastMCP Client with server instance

### 2. **Session Management**  
- **Plugin tests**: Manual session creation via HTTP
- **Server tests**: Mocked connection manager with controlled sessions

### 3. **Tool Access**
- **Plugin tests**: Through HTTP API wrapper
- **Server tests**: Direct MCP protocol via FastMCP Client

### 4. **Response Handling**
- **Plugin tests**: HTTP response parsing
- **Server tests**: Direct MCP tool response objects

## Troubleshooting

### Common Issues

**ImportError: cannot import name 'Client' from 'fastmcp'**
- Ensure FastMCP is installed: `pip install fastmcp`
- Check version compatibility: `pip show fastmcp`

**ModuleNotFoundError: No module named 'remote_server'**
- Run tests from the correct directory: `cd rhino_mcp_remote/tests`
- Verify Python path includes parent directory

**Mock not working properly**
- Ensure patch path matches actual import: `'remote_server.server.connection_manager'`
- Check that mocks are applied before client creation

**Async test failures**
- Install pytest-asyncio: `pip install pytest-asyncio`
- Use `@pytest.mark.asyncio` decorator on async test functions

### Performance Notes

- **In-memory tests** are very fast (milliseconds per test)
- **Full test suite** completes in under 30 seconds
- **No external dependencies** required (Rhino, Redis, etc.)
- **Parallel execution** possible with pytest-xdist

## Integration with Plugin Tests

The server-side tests complement the plugin-side tests:

1. **Server tests** verify MCP tool functionality and logic
2. **Plugin tests** verify end-to-end integration with actual Rhino
3. **Together** they provide complete test coverage

For full system testing, run both:
```bash
# Test server-side MCP tools
cd rhino_mcp_remote/tests
python test_mcp_runner.py

# Test plugin-side integration  
cd reer-rhino-mcp-plugin/tests
python test_runner.py
```

This ensures both the MCP protocol implementation and the Rhino integration work correctly. 