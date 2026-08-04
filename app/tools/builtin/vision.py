"""Built-in Vision tools for screen capture, error explanation, clipboard image reading, and region analysis."""

from typing import Any, Dict, Optional
from app.tools.base import BaseTool
from app.tools.models import ToolPermission, ToolResult
from app.vision.manager import VisionManager


class CaptureScreenTool(BaseTool):
    """Tool to capture full screen or active window and analyze visual content."""

    name = "capture_screen"
    description = "Captures current full screen display or active window and analyzes visual content."
    permission_level = ToolPermission.SAFE

    parameters = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Visual query prompt (e.g. 'What is on my screen?', 'Describe the active window').",
                "default": "Describe what is currently on screen."
            },
            "target": {
                "type": "string",
                "enum": ["fullscreen", "active_window"],
                "description": "Capture target ('fullscreen' or 'active_window').",
                "default": "fullscreen"
            }
        },
        "required": []
    }

    def __init__(self, vision_manager: Optional[VisionManager] = None) -> None:
        self._manager = vision_manager or VisionManager()

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "permission_level": self.permission_level.value,
            "parameters": self.parameters
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        prompt = kwargs.get("prompt", "Describe what is currently on screen.")
        target = kwargs.get("target", "fullscreen").lower()

        try:
            if target == "active_window":
                resp = self._manager.pipeline.process_active_window(prompt=prompt)
            else:
                resp = self._manager.analyze_screen(prompt=prompt)

            return ToolResult(
                tool_name=self.name,
                success=True,
                output={
                    "analysis": resp.text,
                    "ocr_text": resp.ocr_result.text if resp.ocr_result else "",
                    "duration_seconds": resp.duration_seconds
                }
            )
        except Exception as e:
            return ToolResult(tool_name=self.name, success=False, output={}, error=f"Screen capture tool failed: {e}")


class ExplainErrorTool(BaseTool):
    """Tool to capture on-screen error dialogs or terminal stack traces and explain them."""

    name = "explain_error"
    description = "Captures on-screen error dialogs, stack traces, or terminal outputs and provides explanations."
    permission_level = ToolPermission.SAFE

    parameters = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Specific query regarding the error (e.g. 'Read this error and suggest a fix').",
                "default": "Read and explain the error on screen."
            }
        },
        "required": []
    }

    def __init__(self, vision_manager: Optional[VisionManager] = None) -> None:
        self._manager = vision_manager or VisionManager()

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "permission_level": self.permission_level.value,
            "parameters": self.parameters
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        prompt = kwargs.get("prompt", "Read and explain the on-screen error dialog or terminal stack trace.")

        try:
            resp = self._manager.pipeline.process_fullscreen(prompt=prompt, enable_ocr=True)
            ocr_text = resp.ocr_result.text if resp.ocr_result else ""

            return ToolResult(
                tool_name=self.name,
                success=True,
                output={
                    "error_explanation": resp.text,
                    "extracted_error_text": ocr_text,
                    "duration_seconds": resp.duration_seconds
                }
            )
        except Exception as e:
            return ToolResult(tool_name=self.name, success=False, output={}, error=f"Explain error tool failed: {e}")


class ReadClipboardImageTool(BaseTool):
    """Tool to extract text and analyze visual content from system clipboard image."""

    name = "read_clipboard_image"
    description = "Reads image from system clipboard, extracts text via OCR, and provides visual analysis."
    permission_level = ToolPermission.SAFE

    parameters = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Visual query prompt (e.g. 'Extract text from clipboard image').",
                "default": "Describe and extract text from clipboard image."
            }
        },
        "required": []
    }

    def __init__(self, vision_manager: Optional[VisionManager] = None) -> None:
        self._manager = vision_manager or VisionManager()

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "permission_level": self.permission_level.value,
            "parameters": self.parameters
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        prompt = kwargs.get("prompt", "Describe and extract text from clipboard image.")

        try:
            resp = self._manager.analyze_clipboard(prompt=prompt)
            if resp.metadata.get("status") == "empty_clipboard":
                return ToolResult(tool_name=self.name, success=False, output={}, error="No image found in system clipboard.")

            ocr_text = resp.ocr_result.text if resp.ocr_result else ""
            return ToolResult(
                tool_name=self.name,
                success=True,
                output={
                    "analysis": resp.text,
                    "ocr_text": ocr_text,
                    "duration_seconds": resp.duration_seconds
                }
            )
        except Exception as e:
            return ToolResult(tool_name=self.name, success=False, output={}, error=f"Read clipboard image tool failed: {e}")


class AnalyzeRegionTool(BaseTool):
    """Tool to capture specified screen region bounding box and analyze content."""

    name = "analyze_region"
    description = "Captures specified screen bounding box region (x, y, width, height) and analyzes content."
    permission_level = ToolPermission.SAFE

    parameters = {
        "type": "object",
        "properties": {
            "x": {"type": "integer", "description": "Left X coordinate."},
            "y": {"type": "integer", "description": "Top Y coordinate."},
            "width": {"type": "integer", "description": "Region width in pixels."},
            "height": {"type": "integer", "description": "Region height in pixels."},
            "prompt": {
                "type": "string",
                "description": "Visual query prompt for the selected region.",
                "default": "Analyze the selected screen region."
            }
        },
        "required": ["x", "y", "width", "height"]
    }

    def __init__(self, vision_manager: Optional[VisionManager] = None) -> None:
        self._manager = vision_manager or VisionManager()

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "permission_level": self.permission_level.value,
            "parameters": self.parameters
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        x = kwargs.get("x", 0)
        y = kwargs.get("y", 0)
        width = kwargs.get("width", 500)
        height = kwargs.get("height", 500)
        prompt = kwargs.get("prompt", "Analyze the selected screen region.")

        try:
            image = self._manager.capturer.capture_region(x=x, y=y, width=width, height=height)
            resp = self._manager.pipeline.process_image(image, prompt=prompt)

            return ToolResult(
                tool_name=self.name,
                success=True,
                output={
                    "analysis": resp.text,
                    "ocr_text": resp.ocr_result.text if resp.ocr_result else "",
                    "duration_seconds": resp.duration_seconds
                }
            )
        except Exception as e:
            return ToolResult(tool_name=self.name, success=False, output={}, error=f"Analyze region tool failed: {e}")
