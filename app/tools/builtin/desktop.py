"""Built-in tools for desktop interaction and automation."""

from typing import Any, Dict, List, Optional
from app.tools.base import BaseTool
from app.tools.models import ToolPermission
from app.services.desktop.service import DesktopService
from app.core.exceptions import ToolExecutionError


class GetActiveWindowTool(BaseTool):
    """Tool to inspect active foreground window details."""

    def __init__(self, service: DesktopService) -> None:
        self._service = service

    @property
    def name(self) -> str:
        return "get_active_window"

    @property
    def description(self) -> str:
        return (
            "Inspect details of the currently active foreground window "
            "(returns window ID, title, and process name)."
        )

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.SAFE

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        }

    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        try:
            window = self._service.get_active_window()
            return {
                "window_id": window.window_id,
                "title": window.title,
                "process_id": window.process_id,
                "process_name": window.process_name,
                "is_foreground": window.is_foreground,
            }
        except Exception as e:
            raise ToolExecutionError(f"Failed to get active window: {e}") from e


class ListVisibleWindowsTool(BaseTool):
    """Tool to list visible top-level windows."""

    def __init__(self, service: DesktopService) -> None:
        self._service = service

    @property
    def name(self) -> str:
        return "list_visible_windows"

    @property
    def description(self) -> str:
        return "List details (ID, title, process name) of all visible top-level windows."

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.SAFE

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        }

    def execute(self, **kwargs: Any) -> List[Dict[str, Any]]:
        try:
            windows = self._service.list_visible_windows()
            return [
                {
                    "window_id": w.window_id,
                    "title": w.title,
                    "process_name": w.process_name,
                    "is_foreground": w.is_foreground,
                }
                for w in windows
            ]
        except Exception as e:
            raise ToolExecutionError(f"Failed to list visible windows: {e}") from e


class FocusWindowTool(BaseTool):
    """Tool to focus a window by its stable ID."""

    def __init__(self, service: DesktopService) -> None:
        self._service = service

    @property
    def name(self) -> str:
        return "focus_window"

    @property
    def description(self) -> str:
        return "Switch desktop focus to the specified window by stable ID or name/title query (e.g. 'Notepad')."

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.CONFIRMATION

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "window_id": {
                        "type": "string",
                        "description": "The stable runtime window ID (e.g. 'win_a13f82c1') or title/process name query (e.g. 'Notepad') to focus.",
                    }
                },
                "required": ["window_id"],
            },
        }

    def execute(self, **kwargs: Any) -> str:
        window_id = kwargs.get("window_id")
        try:
            self._service.focus_window(window_id)
            return "Window focused successfully."
        except Exception as e:
            raise ToolExecutionError(f"Failed to focus window: {e}") from e

    def get_approval_metadata(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {}
        window_id = arguments.get("window_id")
        if window_id:
            metadata["window_id"] = window_id
            
            # Resolve to get details for approval presentation
            hwnd = self._service._id_to_hwnd.get(window_id)
            if not hwnd:
                res = self._service.resolve_window(window_id)
                if res.status == "RESOLVED" and res.window:
                    hwnd = self._service._id_to_hwnd.get(res.window.window_id)

            if hwnd and self._service._backend.is_window_valid(hwnd):
                details = self._service._backend._get_window_details(hwnd)
                if details:
                    metadata["window_title"] = details[1]
                    metadata["process_name"] = details[3]
        return metadata


class TypeTextTool(BaseTool):
    """Tool to type text in the active window."""

    def __init__(self, service: DesktopService, approval_manager: Any = None) -> None:
        self._service = service
        self._approval_manager = approval_manager
        self.current_approval_action_id: Optional[str] = None

    @property
    def name(self) -> str:
        return "type_text"

    @property
    def description(self) -> str:
        return "Type text input into the currently focused active window."

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.CONFIRMATION

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text string to type into the active window.",
                    }
                },
                "required": ["text"],
            },
        }

    def execute(self, **kwargs: Any) -> str:
        text = kwargs.get("text")
        expected_id = self._get_expected_foreground_id()
        try:
            self._service.type_text(text, expected_foreground_id=expected_id)
            return "Text input was sent successfully."
        except Exception as e:
            raise ToolExecutionError(f"Failed to type text: {e}") from e

    def get_approval_metadata(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        metadata = _capture_active_window_metadata(self._service)
        text = arguments.get("text", "")
        metadata["character_count"] = len(text)
        metadata["preview"] = text[:80]
        return metadata

    def _get_expected_foreground_id(self) -> Optional[str]:
        if self.current_approval_action_id and self._approval_manager:
            action = self._approval_manager.get(self.current_approval_action_id)
            if action and action.metadata:
                return action.metadata.get("expected_foreground_window_id")
        return None


class PressKeyTool(BaseTool):
    """Tool to press a single key in the active window."""

    def __init__(self, service: DesktopService, approval_manager: Any = None) -> None:
        self._service = service
        self._approval_manager = approval_manager
        self.current_approval_action_id: Optional[str] = None

    @property
    def name(self) -> str:
        return "press_key"

    @property
    def description(self) -> str:
        return "Press an allowed keyboard key (e.g. enter, tab, escape, up, down)."

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.CONFIRMATION

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "The key name to press (e.g., 'enter', 'tab', 'escape').",
                    }
                },
                "required": ["key"],
            },
        }

    def execute(self, **kwargs: Any) -> str:
        key = kwargs.get("key")
        expected_id = self._get_expected_foreground_id()
        try:
            self._service.press_key(key, expected_foreground_id=expected_id)
            return "Keypress sent successfully."
        except Exception as e:
            raise ToolExecutionError(f"Failed to press key: {e}") from e

    def get_approval_metadata(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        metadata = _capture_active_window_metadata(self._service)
        metadata["key"] = arguments.get("key")
        return metadata

    def _get_expected_foreground_id(self) -> Optional[str]:
        if self.current_approval_action_id and self._approval_manager:
            action = self._approval_manager.get(self.current_approval_action_id)
            if action and action.metadata:
                return action.metadata.get("expected_foreground_window_id")
        return None


class PressHotkeyTool(BaseTool):
    """Tool to press a hotkey combination in the active window."""

    def __init__(self, service: DesktopService, approval_manager: Any = None) -> None:
        self._service = service
        self._approval_manager = approval_manager
        self.current_approval_action_id: Optional[str] = None

    @property
    def name(self) -> str:
        return "press_hotkey"

    @property
    def description(self) -> str:
        return "Execute an approved keyboard shortcut combination (e.g., ctrl+s, ctrl+c)."

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.CONFIRMATION

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "keys": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of keys representing the combination (e.g. ['ctrl', 's']).",
                    }
                },
                "required": ["keys"],
            },
        }

    def execute(self, **kwargs: Any) -> str:
        keys = kwargs.get("keys")
        expected_id = self._get_expected_foreground_id()
        try:
            self._service.press_hotkey(keys, expected_foreground_id=expected_id)
            return "Hotkey combination sent successfully."
        except Exception as e:
            raise ToolExecutionError(f"Failed to execute hotkey: {e}") from e

    def get_approval_metadata(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        metadata = _capture_active_window_metadata(self._service)
        metadata["keys"] = arguments.get("keys")
        return metadata

    def _get_expected_foreground_id(self) -> Optional[str]:
        if self.current_approval_action_id and self._approval_manager:
            action = self._approval_manager.get(self.current_approval_action_id)
            if action and action.metadata:
                return action.metadata.get("expected_foreground_window_id")
        return None


class ClickScreenTool(BaseTool):
    """Tool to send mouse clicks at specific coordinates."""

    def __init__(self, service: DesktopService, approval_manager: Any = None) -> None:
        self._service = service
        self._approval_manager = approval_manager
        self.current_approval_action_id: Optional[str] = None

    @property
    def name(self) -> str:
        return "click_screen"

    @property
    def description(self) -> str:
        return "Perform a bounded mouse click at coordinates (x, y)."

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.CONFIRMATION

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {
                        "type": "integer",
                        "description": "Screen coordinate X.",
                    },
                    "y": {
                        "type": "integer",
                        "description": "Screen coordinate Y.",
                    },
                    "button": {
                        "type": "string",
                        "description": "Mouse button ('left' or 'right').",
                    },
                },
                "required": ["x", "y", "button"],
            },
        }

    def execute(self, **kwargs: Any) -> str:
        x = kwargs.get("x")
        y = kwargs.get("y")
        button = kwargs.get("button")
        expected_id = self._get_expected_foreground_id()
        try:
            self._service.click_screen(x, y, button, expected_foreground_id=expected_id)
            return "Mouse click sent successfully."
        except Exception as e:
            raise ToolExecutionError(f"Failed mouse click: {e}") from e

    def get_approval_metadata(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        metadata = _capture_active_window_metadata(self._service)
        metadata["x"] = arguments.get("x")
        metadata["y"] = arguments.get("y")
        metadata["button"] = arguments.get("button")
        return metadata

    def _get_expected_foreground_id(self) -> Optional[str]:
        if self.current_approval_action_id and self._approval_manager:
            action = self._approval_manager.get(self.current_approval_action_id)
            if action and action.metadata:
                return action.metadata.get("expected_foreground_window_id")
        return None


def _capture_active_window_metadata(service: DesktopService) -> Dict[str, Any]:
    """Helper to capture active window details for approval metadata."""
    metadata: Dict[str, Any] = {}
    try:
        active = service.get_active_window()
        metadata["expected_foreground_window_id"] = active.window_id
        metadata["expected_foreground_window_title"] = active.title
        metadata["expected_foreground_process_name"] = active.process_name
    except Exception:
        pass
    return metadata
