"""Domain models and metrics for desktop interaction service."""

from dataclasses import dataclass, field
from typing import Dict, Any
from types import MappingProxyType
import threading


@dataclass(frozen=True)
class DesktopWindow:
    """Immutable domain model representing a visible or active desktop window."""
    window_id: str
    title: str
    process_id: int
    process_name: str
    is_visible: bool
    is_foreground: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Defensively copy metadata and make it read-only
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


class DesktopMetrics:
    """Lightweight thread-safe metrics tracker for desktop interaction actions."""
    
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.active_window_requests = 0
        self.window_list_requests = 0
        self.window_resolution_requests = 0
        self.focus_requests = 0
        self.type_requests = 0
        self.key_requests = 0
        self.hotkey_requests = 0
        self.click_requests = 0
        self.successful_actions = 0
        self.failed_actions = 0
        self.foreground_change_blocks = 0
        self.stale_window_blocks = 0

    def increment(self, name: str) -> None:
        with self._lock:
            if hasattr(self, name):
                setattr(self, name, getattr(self, name) + 1)

    def to_dict(self) -> Dict[str, int]:
        with self._lock:
            return {
                "active_window_requests": self.active_window_requests,
                "window_list_requests": self.window_list_requests,
                "window_resolution_requests": self.window_resolution_requests,
                "focus_requests": self.focus_requests,
                "type_requests": self.type_requests,
                "key_requests": self.key_requests,
                "hotkey_requests": self.hotkey_requests,
                "click_requests": self.click_requests,
                "successful_actions": self.successful_actions,
                "failed_actions": self.failed_actions,
                "foreground_change_blocks": self.foreground_change_blocks,
                "stale_window_blocks": self.stale_window_blocks,
            }
