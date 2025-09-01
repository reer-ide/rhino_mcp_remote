"""Tools for interacting with Replicate's Flux Depth model."""
from typing import Optional
import os
import requests
import base64
import io
import time
from PIL import Image as PILImage
from datetime import datetime

from mcp.types import ImageContent
from remote_server.connection_manager import ConnectionManager
from remote_server.utils.tool_helpers import handle_error
from remote_server.utils.rhino_commands import RhinoCommand
from remote_server.config import settings


def register_tools(mcp, connection_manager: Optional[ConnectionManager]):
	"""Register AI render tools with the MCP server."""
	
	@mcp.tool()
	async def ai_render_rhino_scene(session_id: str, prompt: str, max_size: int = 800) -> ImageContent:
		"""Use Replicate Flux-Depth to stylize the current Rhino viewport based on a text prompt.
		
		This tool:
		1. Captures the current Rhino viewport using capture_rhino_viewport
		2. Sends the image and prompt to Replicate's Flux-Depth AI model
		3. Returns the AI-stylized rendering as an ImageContent object
		4. Saves both input and output images to tests/ai directory with timestamps
		
		Requires REPLICATE_TOKEN environment variable or settings.replicate_token.
		
		Args:
			session_id: Active Rhino session id
			prompt: Text prompt to guide the rendering (e.g., "futuristic cyberpunk style", "watercolor painting")
			max_size: Max output size in pixels (keeps aspect ratio, default: 800)
			
		Returns:
			ImageContent object containing the AI-rendered image as base64 JPEG data.
			
			On error returns error message via handle_error utility.
		"""
		try:
			# 1) Capture Rhino viewport as base64 via the session's WebSocket
			from remote_server.dependencies import get_connection_manager
			conn_mgr = await get_connection_manager()
			capture_params = {
				"layer": None,
				"show_annotations": False,
				"max_size": max_size,
			}
			capture_result = await conn_mgr.send_to_rhino(session_id, RhinoCommand.CAPTURE_VIEWPORT, capture_params)

			# Normalize possible wrapped response structure
			actual = capture_result
			if isinstance(capture_result, dict) and capture_result.get("type") == "response" and "result" in capture_result:
				actual = capture_result["result"]

			if not isinstance(actual, dict) or actual.get("type") != "image":
				raise RuntimeError("Viewport capture failed: unexpected response")

			source = actual.get("source", {})
			if source.get("type") != "base64" or not source.get("data"):
				raise RuntimeError("Viewport capture missing base64 data")

			viewport_base64 = source["data"]
			media_type = source.get("media_type", "image/jpeg")

			# Save input image to tests/ai with timestamped filename
			ts = datetime.now().strftime("%Y%m%d_%H%M%S")
			repo_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
			save_dir = os.path.join(repo_root, "tests", "ai")
			os.makedirs(save_dir, exist_ok=True)
			input_ext = "jpg" if "jpeg" in media_type else ("png" if "png" in media_type else "jpg")
			input_path = os.path.join(save_dir, f"{ts}_input.{input_ext}")
			with open(input_path, "wb") as f:
				f.write(base64.b64decode(viewport_base64))

			# 2) Prepare Replicate API token and headers (.env through settings + env fallback)
			token_candidates = [
				settings.replicate_token,
				os.environ.get("REPLICATE_API_TOKEN"),
				os.environ.get("REPLICATE_TOKEN"),
				os.environ.get("REPLICATE_SECRET"),
				os.environ.get("REPLICATE_SECERT"),
			]
			api_token = next((t for t in token_candidates if t), None)
			# Debug log: indicate whether token is visible (without printing it)
			print(f"[AI] Replicate token visible: {bool(api_token)} (settings: {bool(settings.replicate_token)})")
			if not api_token:
				raise RuntimeError("Missing Replicate API token (REPLICATE_TOKEN)")

			headers = {
				"Authorization": f"Token {api_token}",
				"Content-Type": "application/json",
			}

			# 3) Start prediction (model identifier per Replicate docs)
			start_resp = requests.post(
				"https://api.replicate.com/v1/predictions",
				json={
					"version": "black-forest-labs/flux-depth-dev",
					"input": {
						"prompt": prompt,
						"control_image": f"data:image/jpeg;base64,{viewport_base64}",
					},
				},
				headers=headers,
				timeout=30,
			)
			start_resp.raise_for_status()
			prediction = start_resp.json()
			prediction_url = prediction.get("urls", {}).get("get")
			if not prediction_url:
				raise RuntimeError("Replicate response missing prediction URL")

			# 4) Poll for result (up to ~60s)
			deadline = time.time() + 60
			output_url: Optional[str] = None
			while time.time() < deadline:
				# note: requests is blocking; acceptable for short polling in this async tool, consistent with other tools
				resp = requests.get(prediction_url, headers=headers, timeout=15)
				resp.raise_for_status()
				pred = resp.json()
				status = pred.get("status")
				if status == "succeeded" and pred.get("output"):
					out = pred["output"]
					output_url = out[0] if isinstance(out, list) else out
					break
				if status in ("failed", "canceled", "error"):
					raise RuntimeError(f"Replicate prediction failed: {status}")
				time.sleep(2)

			if not output_url:
				raise TimeoutError("Replicate prediction timed out")

			# 5) Download and post-process image, then return ImageContent with base64
			img_bytes = requests.get(output_url, timeout=30).content
			img = PILImage.open(io.BytesIO(img_bytes))
			if img.width > max_size or img.height > max_size:
				ratio = max_size / max(img.width, img.height)
				img = img.resize((int(img.width * ratio), int(img.height * ratio)), PILImage.Resampling.LANCZOS)

			buffer = io.BytesIO()
			img.save(buffer, format="JPEG", quality=70, optimize=True)
			out_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

			# Save output image alongside input
			output_path = os.path.join(save_dir, f"{ts}_output.jpg")
			with open(output_path, "wb") as f:
				f.write(buffer.getvalue())

			return ImageContent(type="image", data=out_b64, mimeType="image/jpeg", annotations=None)

		except Exception as e:
			return handle_error("AI rendering Rhino scene", session_id, e)
