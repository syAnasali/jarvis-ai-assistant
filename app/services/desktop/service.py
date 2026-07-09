"""Desktop service orchestrating policy checks, stable ID mappings, and backend interactions."""

import os
import time
import hashlib
from typing import Dict, List, Optional, Tuple
from app.services.desktop.models import DesktopWindow, DesktopMetrics
from app.services.desktop.policy import DesktopPolicy
from app.services.desktop.resolver import DesktopResolver, ResolutionResult
from app.services.desktop.backend import DesktopBackend, WindowsDesktopBackend
from app.core.exceptions import (
    WindowNotFoundError,
    WindowAmbiguousError,
    WindowStaleError,
    WindowNotVisibleError,
    FocusFailedError,
    ForegroundChangedError,
)
from app.core.logger import JarvisLogger

logger = JarvisLogger.get_logger("desktop_service")


class DesktopService:
    """Core service for managing desktop automation window identity, safety, and action dispatching."""

    def __init__(
        self,
        policy: DesktopPolicy,
        resolver: DesktopResolver,
        backend: Optional[DesktopBackend] = None,
        list_limit: int = 50,
        text_max_chars: int = 5000,
    ) -> None:
        self._policy = policy
        self._resolver = resolver
        self._backend = backend or WindowsDesktopBackend()
        self._list_limit = list_limit
        self._text_max_chars = text_max_chars
        self.metrics = DesktopMetrics()

        # In-memory mapping: HWND (int) <-> window_id (str)
        self._hwnd_to_id: Dict[int, str] = {}
        self._id_to_hwnd: Dict[str, int] = {}

    def get_active_window(self) -> DesktopWindow:
        """Retrieves the current active foreground window.

        Returns:
            DesktopWindow: Immutable domain model of the foreground window.
        """
        self.metrics.increment("active_window_requests")
        active = self._backend.get_foreground_window()
        if not active:
            raise WindowNotFoundError("No active foreground window detected.")

        hwnd, title, pid, proc_name = active
        win_id = self._get_or_register_hwnd(hwnd)
        
        # Check if visible (active foreground is visible by definition, but verify)
        return DesktopWindow(
            window_id=win_id,
            title=title,
            process_id=pid,
            process_name=proc_name,
            is_visible=True,
            is_foreground=True,
        )

    def list_visible_windows(self) -> List[DesktopWindow]:
        """Lists all top-level visible windows, excluding Jarvis window.

        Returns:
            List[DesktopWindow]: Deterministically sorted list of visible windows.
        """
        self.metrics.increment("window_list_requests")
        raw_windows = self._backend.list_visible_windows()
        
        # Prune stale handles from in-memory maps
        self._prune_stale_handles()

        my_pid = os.getpid()
        visible_windows: List[DesktopWindow] = []

        # Get current foreground window handle to mark is_foreground correctly
        active = self._backend.get_foreground_window()
        active_hwnd = active[0] if active else 0

        for hwnd, title, pid, proc_name in raw_windows:
            # Exclude our own Jarvis process to prevent self-focus loops
            if pid == my_pid:
                continue

            win_id = self._get_or_register_hwnd(hwnd)
            is_foreground = (hwnd == active_hwnd)

            visible_windows.append(DesktopWindow(
                window_id=win_id,
                title=title,
                process_id=pid,
                process_name=proc_name,
                is_visible=True,
                is_foreground=is_foreground,
            ))

        # Deterministic sorting: Title alphabetically, then Window ID
        sorted_wins = sorted(visible_windows, key=lambda w: (w.title.lower(), w.window_id))
        
        # Bound count
        return sorted_wins[:self._list_limit]

    def resolve_window(self, query: str) -> ResolutionResult:
        """Resolves a window name query against visible windows."""
        self.metrics.increment("window_resolution_requests")
        windows = self.list_visible_windows()
        return self._resolver.resolve(query, windows)

    def focus_window(self, window_id: str) -> None:
        """Sets focus to the target window and verifies success.

        Raises:
            WindowNotFoundError: If ID or name is unknown/untracked.
            WindowAmbiguousError: If target name matches multiple windows.
            WindowStaleError: If the underlying native handle is dead.
            WindowNotVisibleError: If the target window is hidden.
            FocusFailedError: If focus verification fails.
        """
        self.metrics.increment("focus_requests")
        hwnd = self._id_to_hwnd.get(window_id)
        
        # Fallback resolution if window_id is not a known registered ID
        if not hwnd:
            res = self.resolve_window(window_id)
            if res.status == "RESOLVED" and res.window:
                window_id = res.window.window_id
                hwnd = self._id_to_hwnd.get(window_id)
            elif res.status == "AMBIGUOUS":
                raise WindowAmbiguousError(
                    f"Target window reference '{window_id}' is ambiguous and matches multiple candidates."
                )

        if not hwnd:
            self.metrics.increment("stale_window_blocks")
            raise WindowNotFoundError(f"Window ID or name '{window_id}' is unknown or stale.")

        if not self._backend.is_window_valid(hwnd):
            self.metrics.increment("stale_window_blocks")
            raise WindowStaleError(f"Window with ID '{window_id}' (handle {hwnd}) is no longer alive.")

        # Ensure it is currently visible
        visible_hwnds = {w[0] for w in self._backend.list_visible_windows()}
        if hwnd not in visible_hwnds:
            raise WindowNotVisibleError(f"Window ID '{window_id}' is currently hidden or minimized and cannot be focused.")

        # Focus operation
        logger.info(f"Focusing window ID {window_id} (HWND {hwnd})")
        success = self._backend.focus_window(hwnd)
        if not success:
            self.metrics.increment("failed_actions")
            raise FocusFailedError("Native focus window invocation returned failure.")

        # Verification step
        time.sleep(0.15)  # Wait for OS window transition
        active = self._backend.get_foreground_window()
        if not active or active[0] != hwnd:
            actual_title = active[1] if active else "None"
            self.metrics.increment("failed_actions")
            raise FocusFailedError(
                f"Window focus verification failed. Target HWND {hwnd} is not foreground. Active title: '{actual_title}'"
            )

        self.metrics.increment("successful_actions")
        logger.info(f"Focus window ID {window_id} verified successfully.")

    def type_text(self, text: str, expected_foreground_id: Optional[str] = None) -> None:
        """Sends unicode keystrokes to the active window after validating constraints."""
        self.metrics.increment("type_requests")
        self._policy.validate_text(text, self._text_max_chars)

        # Enforce foreground safety guard
        self._verify_foreground_guard(expected_foreground_id)

        logger.info(f"Typing text (chars: {len(text)}) into foreground window.")
        self._backend.type_text(text)
        self.metrics.increment("successful_actions")

    def press_key(self, key: str, expected_foreground_id: Optional[str] = None) -> None:
        """Sends a single keypress to the focused window."""
        self.metrics.increment("key_requests")
        self._policy.validate_key(key)

        # Enforce foreground safety guard
        self._verify_foreground_guard(expected_foreground_id)

        logger.info(f"Pressing key '{key}' in foreground window.")
        self._backend.press_key(key)
        self.metrics.increment("successful_actions")

    def press_hotkey(self, keys: List[str], expected_foreground_id: Optional[str] = None) -> None:
        """Sends a shortcut key combination to the focused window."""
        self.metrics.increment("hotkey_requests")
        canonical_keys = self._policy.canonicalize_hotkey(keys)

        # Enforce foreground safety guard
        self._verify_foreground_guard(expected_foreground_id)

        logger.info(f"Pressing hotkey shortcut {canonical_keys} in foreground window.")
        self._backend.press_hotkey(canonical_keys)
        self.metrics.increment("successful_actions")

    def click_screen(self, x: int, y: int, button: str, expected_foreground_id: Optional[str] = None) -> None:
        """Performs a mouse click at the screen coordinates."""
        self.metrics.increment("click_requests")
        btn = self._policy.validate_button(button)
        width, height = self._backend.get_screen_dimensions()
        self._policy.validate_coordinates(x, y, width, height)

        # Enforce foreground safety guard
        self._verify_foreground_guard(expected_foreground_id)

        logger.info(f"Clicking mouse {btn} button at ({x}, {y}) in foreground window.")
        self._backend.click_screen(x, y, btn)
        self.metrics.increment("successful_actions")

    def wait_for_window(
        self,
        query: str,
        timeout_seconds: float = 10.0,
        poll_interval_ms: int = 200,
    ) -> DesktopWindow:
        """Polls visible windows until a matching window is found or timeout occurs."""
        start_time = time.monotonic()
        poll_secs = poll_interval_ms / 1000.0

        while (time.monotonic() - start_time) < timeout_seconds:
            res = self.resolve_window(query)
            if res.status == "RESOLVED" and res.window:
                return res.window
            
            time.sleep(poll_secs)

        raise WindowNotFoundError(f"Window matching query '{query}' was not found within {timeout_seconds} seconds.")

    def _get_or_register_hwnd(self, hwnd: int) -> str:
        """Retrieves or creates a stable runtime window ID for the given handle."""
        if hwnd in self._hwnd_to_id:
            return self._hwnd_to_id[hwnd]

        # Generate stable runtime ID (win_ + md5 of handle)
        win_id = f"win_{hashlib.md5(str(hwnd).encode('utf-8')).hexdigest()[:8]}"
        self._hwnd_to_id[hwnd] = win_id
        self._id_to_hwnd[win_id] = hwnd
        return win_id

    def _verify_foreground_guard(self, expected_foreground_id: Optional[str]) -> None:
        """Guards against active window changes between approval and execution."""
        if expected_foreground_id is None:
            return

        active = self._backend.get_foreground_window()
        if not active:
            self.metrics.increment("foreground_change_blocks")
            raise ForegroundChangedError("Foreground safety guard failed: No active window detected.")

        active_hwnd, title, pid, proc_name = active
        active_id = self._get_or_register_hwnd(active_hwnd)

        if active_id != expected_foreground_id:
            self.metrics.increment("foreground_change_blocks")
            logger.warning(
                f"ForegroundChangedError: Expected window ID '{expected_foreground_id}', "
                f"but active foreground window is ID '{active_id}' (Title: '{title}')."
            )
            raise ForegroundChangedError(
                "Foreground safety guard blocked execution: Active focus switched to another window."
            )

    def _prune_stale_handles(self) -> None:
        """Prunes dead window handles from internal registries."""
        stale_hwnds = [hwnd for hwnd in self._hwnd_to_id.keys() if not self._backend.is_window_valid(hwnd)]
        for hwnd in stale_hwnds:
            win_id = self._hwnd_to_id.pop(hwnd, None)
            if win_id:
                self._id_to_hwnd.pop(win_id, None)
