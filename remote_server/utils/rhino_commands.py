"""Centralized command names for Rhino plugin WebSocket protocol.

Use these constants instead of hardcoded strings when sending commands
via ConnectionManager.send_to_rhino to avoid typos and ease refactors.
"""

class RhinoCommand:
	CAPTURE_VIEWPORT = "capture_rhino_viewport"
	# Add more as needed across the codebase:
	CREATE_LAYERS = "create_rhino_layers"
	DELETE_LAYERS = "delete_rhino_layers"
	CREATE_BASIC_GEOMETRIES = "create_rhino_basic_geometries"
	DELETE_OBJECTS = "delete_rhino_objects"
	MODIFY_OBJECTS = "modify_rhino_objects"
	GET_SCENE_INFO = "get_rhino_scene_info"
	GET_OBJECTS_INFO = "get_rhino_objects_info"
	GET_SELECTED_OBJECTS = "get_rhino_selected_objects"
	SELECT_FILTERED_OBJECTS = "select_filtered_rhino_objects"
	EXECUTE_RHINO_SCRIPT = "execute_rhino_script"
