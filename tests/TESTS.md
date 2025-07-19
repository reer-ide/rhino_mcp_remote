# Remote MCP Server Tests

Streamlined test suite for the Remote Rhino MCP Server with both fast unit tests and complete integration tests.

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
# cd to the reer-rhino-mcp-plugin directory
# run the following command to install the plugin
dotnet build
# the plugin will be built in the bin/Debug/net7.0/reer-rhino-mcp-plugin.rhp file
# open vs code and launch the debugger with "Rhino 8-netcore", this will open the test rhino instance and load the plugin automatically
# if the plugin is not loaded, you can load it through the PluginManger manually

# 3. Run integration tests (in new terminal)
cd rhino_mcp_remote/tests  
python run_integration_tests.py integration

# 4. after registering the license with the server, you can run the tool call tests quickly by running the following command
python .\tests\test_integration_connected_flow.py quick
# this will skip the license registration and session creation steps, and directly run the tool call tests
```

## Test Files

- **`test_all_mcp_tools.py`** - Unit tests for all 13 MCP tools (FastMCP in-memory)
- **`test_mcp_scenarios.py`** - Workflow scenario tests  
- **`test_mcp_runner.py`** - Master runner for unit tests
- **`test_integration_connected_flow.py`** - End-to-end tests with real Rhino connection
- **`run_integration_tests.py`** - Master runner for integration tests
- **`test_tools_import.py`** - Import validation

## Integration Test Setup

### Prerequisites
- Rhino 8+ with RhinoMCP plugin loaded
- Remote server running on http://127.0.0.1:8080

### User Actions Required
1. **License Registration**: Run `ReerRegister` in Rhino with provided license key
2. **Connection**: Run `ReerStart` → choose 'remote' in Rhino with open document

### What Gets Tested
- License generation and registration flow
- Session creation and management  
- 8 core MCP tools with actual Rhino responses:
  - `get_rhino_scene_info`
  - `create_rhino_basic_objects` 
  - `add_rhino_objects_metadata`
  - `create_rhino_layers`
  - `select_rhino_objects`
  - `get_rhino_selected_objects`
  - `get_rhino_objects_info`
  - `capture_rhino_viewport`

## Troubleshooting

**Server connection failed**: Ensure server is running and port 8080 is free

**ReerRegister command not found**: Plugin not loaded - rebuild/reinstall plugin

**No active session found**: Run `ReerStart` → 'remote' with Rhino document open

**License registration failed**: Copy license key and user ID exactly as shown

## Test Results

- Unit tests: JSON report in `mcp_test_results.json`
- Integration tests: JSON report in `integration_test_results.json`  
- Success rate shown in console output

## Coverage

- **13 MCP tools** tested with comprehensive unit tests
- **8 critical tools** tested with real Rhino integration
- **Complete workflow scenarios** for realistic usage patterns
- **License and session management** end-to-end validation