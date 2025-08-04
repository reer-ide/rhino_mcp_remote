# Remote MCP Server Tests

Comprehensive test suite for the Remote Rhino MCP Server with modular unit tests and full integration tests.

## Quick Start

### Run Unit Tests (Fast)
```bash
cd rhino_mcp_remote/tests
python test_mcp_runner.py
```

### Run Integration Tests (Requires Rhino)
```bash
# 1. Start server
python -m remote_server.server

# 2. Install the Rhino MCP plugin
# Build for Debug (includes all commands and dev features)
cd reer-rhino-mcp-plugin
dotnet build
# Launch with VS Code debugger "Rhino 8-netcore" to auto-load plugin

# 3. Run integration tests (in new terminal)
cd rhino_mcp_remote/tests  

# Full integration test (license + sessions + tools)
python test_integration_connected_flow.py

# Quick tool test (uses existing connected sessions) 
python test_integration_connected_flow.py quick

# Connection test only (no tool testing)
python test_integration_connected_flow.py connection

# Show help
python test_integration_connected_flow.py help
```

## Test Structure

### Unit Tests
- **`test_all_mcp_tools.py`** - Unit tests for all 13 MCP tools (FastMCP in-memory)
- **`test_mcp_scenarios.py`** - Workflow scenario tests  
- **`test_mcp_runner.py`** - Master runner for unit tests
- **`test_tools_import.py`** - Import validation

### Integration Tests (Modular)
- **`test_integration_connected_flow.py`** - Main test runner
- **`integration/`** - Modular test components:
  - **`base_tester.py`** - Base class with common functionality
  - **`license_tester.py`** - License generation and registration
  - **`session_tester.py`** - Session creation and management
  - **`mcp_tools_tester.py`** - Comprehensive MCP tool testing
  - **`quick_tester.py`** - Quick tests using existing sessions
  - **`connected_flow_tester.py`** - Main integration test orchestrator

## Integration Test Setup

### Prerequisites
- Rhino 8+ with RhinoMCP plugin loaded
- Remote server running on http://127.0.0.1:8080

### User Actions Required
1. **License Registration**: Run `ReerRegister` in Rhino with provided license key
2. **Connection**: Run `ReerStart` → choose 'remote' in Rhino with open document

### What Gets Tested
**12-Phase Integration Workflow:**
1. **Scene Assessment** - Extract units, auto-scale objects based on document units (mm→100x, m→0.1x)
2. **Layer Creation** - Create test layer with color
3. **Object Creation** - Box, sphere, cylinder with proper scaling
4. **Metadata Management** - Add/update object names and descriptions  
5. **Information Retrieval** - Query objects with attributes
6. **Selection & Modification** - Chained operations (rotate→translate→recolor) with sequential execution
7. **Viewport Capture** - Screenshot with auto-decode and save (PNG files)
8. **Script Execution** - Complex spiral curve via rhinoscriptsyntax
9. **Visual Verification** - Interactive inspection before cleanup
10. **Final Assessment** - Compare end vs initial state
11. **Cleanup** - Delete all test objects and layers
12. **Verification** - Ensure complete cleanup

**13 MCP Tools Tested:**
- Scene info, object creation/modification/deletion  
- Layer management, metadata operations
- Selection tools, viewport capture, script execution

## New Test Features

### Unit-Aware Scaling
Objects automatically scaled for visibility based on document units:
- **Millimeters**: 100x scale (500mm box instead of 5mm)
- **Meters**: 0.1x scale  
- **Imperial**: 10x scale

### Interactive Visual Verification
Test pauses before cleanup for manual inspection:
```
👁️ VISUAL INSPECTION REQUIRED
📋 Expected objects (scaled 100.0x for Millimeters):
  • TestBox_1 - 500×300×200mm - rotated and moved
  • TestSphere_1 - 200mm radius - blue color
  • IntegrationTest_Spiral - complex curve

✅ Can you see the expected objects? (y/n/s):
```

### Automatic Screenshot Capture
Viewport images auto-decoded and saved:
```
📸 Viewport captured (285ms)
💾 Image saved: viewport_capture_20250723_143022.png
```

## Troubleshooting

**Server connection failed**: Ensure server running on port 8080

**Plugin not loaded**: Rebuild plugin, check PluginManager and right click on the plugin and select "Load"

**No active session**: Run `ReerStart` → 'remote' with open document, Run `ReerRestart` to restart the connection with a new session (if you have restarted the server, you need to restart the connection)

**Objects too small**: Check unit scaling in console output

**Modify test skipped**: Check object ID extraction messages

**Objects not found**: Check object ID extraction messages

## Test Results & Artifacts

**Generated Files:**
- `integration_test_results.json` - Detailed test report with performance metrics
- `viewport_capture_YYYYMMDD_HHMMSS.png` - Screenshot captures  
- Console logs with object IDs, scaling factors, and execution times

**Expected Success Rate:** 100% (13/13 tools passing)

## Coverage

- **13 MCP tools** with comprehensive integration testing
- **12-phase workflow** covering complete CAD operations  
- **Unit-aware scaling** for all document types
- **Visual verification** with interactive inspection
- **Error handling** with graceful fallbacks
- **License and session management** end-to-end validation