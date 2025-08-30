"""
AI render tool tester for integration testing
"""

import asyncio
import json
from typing import Dict, Any, Optional, List

# Support both module and standalone execution
try:
	from .session_tester import SessionTester
	from .mcp_tools_tester import MCPToolsTester
except ImportError:
	import os
	sys_path_added = False
	try:
		import sys
		import os as _os
		# Add project root to sys.path
		_root = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
		if _root not in sys.path:
			sys.path.insert(0, _root)
			sys_path_added = True
		from tests.integration.session_tester import SessionTester
		from tests.integration.mcp_tools_tester import MCPToolsTester
	except Exception:
		raise


class AIRenderTester(SessionTester, MCPToolsTester):
	"""Tester for the ai_render_rhino_scene MCP tool"""

	async def test_ai_render(self, prompt: str, max_size: int = 800) -> bool:
		"""Find an active session and invoke ai_render_rhino_scene.
		Returns True on success (tool call returned content), False otherwise.
		"""
		# Step 1: Check server
		print("[TEST] AI Render Tool Test")
		print("=" * 60)
		if not await self.check_server_running():
			print("[ERROR] Server is not running. Please start the server first.")
			return False

		# Step 2: Find active sessions
		print("\nStep 2: Looking for connected sessions...")
		connected_sessions = await self.get_active_sessions_for_user()
		if not connected_sessions:
			print("[ERROR] No connected sessions found. Make sure the Rhino plugin is connected.")
			return False

		# Use the first connected session
		session = connected_sessions[0]
		self.session_data_list = [session]
		self.session_data = session
		self.license_data = {
			'license_id': session.get('license_id'),
			'issued_to': self.test_user_id,
		}
		print(f"[INFO] Using session: {session['session_id'][:8]}... for AI render")

		# Step 3: Call the tool
		print("\nStep 3: Calling ai_render_rhino_scene...")
		result = await self.test_mcp_tool_call(
			"ai_render_rhino_scene",
			{"prompt": prompt, "max_size": max_size},
			None,  # Image content; no JSON field checks
		)

		# Step 4: Summarize
		test_results = {
			'total': 1,
			'passed': 1 if result.get('status') == 'PASS' else 0,
			'failed': 0 if result.get('status') == 'PASS' else 1,
		}
		return self.print_test_summary(test_results)


async def _run_standalone():
	"""Entry point for running this tester standalone"""
	tester = AIRenderTester()
	prompt = "A cinematic photo of a modern architectural facade at golden hour, soft shadows"
	try:
		user_prompt = input("Enter AI render prompt (press Enter to use default): ").strip()
		if user_prompt:
			prompt = user_prompt
	except EOFError:
		print("Using default prompt (non-interactive mode)")
	return await tester.test_ai_render(prompt)


def _main():
	ok = asyncio.run(_run_standalone())
	raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
	_main()
