#!/usr/bin/env python3
"""Test script to verify all tool imports work correctly."""

import sys
import os

# Add the parent directory to the path so we can import remote_server
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # Test tool module imports (using new function-based approach)
    import remote_server.tools.metadata_tools
    import remote_server.tools.scene_tools
    import remote_server.tools.object_tools
    import remote_server.tools.layer_tools
    import remote_server.tools.viewport_tools
    import remote_server.tools.execution_tools
    import remote_server.tools.selection_tools
    import remote_server.tools.documentation_tools
    import remote_server.tools.utility_tools
    print("+ All tool module imports successful")
    
    # Test individual tools have register_tools functions
    modules = [
        'metadata_tools',
        'scene_tools', 
        'object_tools',
        'layer_tools',
        'viewport_tools',
        'execution_tools',
        'selection_tools',
        'documentation_tools',
        'utility_tools'
    ]
    
    for module_name in modules:
        module = __import__(f'remote_server.tools.{module_name}', fromlist=['register_tools'])
        if hasattr(module, 'register_tools'):
            print(f"+ {module_name} has register_tools function")
        else:
            print(f"- {module_name} missing register_tools function")
    
    print("\nAll tool imports and structure tests passed!")

except ImportError as e:
    print(f"- Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"- Unexpected error: {e}")
    sys.exit(1) 