"""Abstract and Windows implementation of the desktop interaction backend."""

import time
import abc
import ctypes
from ctypes import wintypes
from typing import List, Tuple, Optional, Dict
import psutil
from app.core.exceptions import DesktopBackendError

# Virtual key code mapping for allowed keys, modifiers, and alphabetic shortcuts
VK_MAP: Dict[str, int] = {
    "enter": 0x0D,
    "tab": 0x09,
    "escape": 0x1B,
    "backspace": 0x08,
    "delete": 0x2E,
    "up": 0x26,
    "down": 0x28,
    "left": 0x25,
    "right": 0x27,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21,
    "pagedown": 0x22,
    "ctrl": 0x11,
    "alt": 0x12,
    "shift": 0x10,
}
for char_code in range(ord("a"), ord("z") + 1):
    VK_MAP[chr(char_code)] = 0x41 + (char_code - ord("a"))


# Win32 SendInput structures for robust keystrokes
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulonglong),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulonglong),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("ki", KEYBDINPUT),
        ("mi", MOUSEINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUT_UNION),
    ]


class DesktopBackend(abc.ABC):
    """Abstract interface for interacting with the operating system desktop."""

    @abc.abstractmethod
    def get_foreground_window(self) -> Optional[Tuple[int, str, int, str]]:
        """Retrieves details of the current foreground active window.

        Returns:
            Tuple[hwnd, title, pid, process_name] or None.
        """
        pass

    @abc.abstractmethod
    def list_visible_windows(self) -> List[Tuple[int, str, int, str]]:
        """Lists all top-level visible windows.

        Returns:
            List of Tuple[hwnd, title, pid, process_name].
        """
        pass

    @abc.abstractmethod
    def focus_window(self, hwnd: int) -> bool:
        """Brings the specified window handle to the foreground and active focus.

        Returns:
            bool: True if successful, False otherwise.
        """
        pass

    @abc.abstractmethod
    def type_text(self, text: str) -> None:
        """Sends unicode text typing keystrokes to the focused window."""
        pass

    @abc.abstractmethod
    def press_key(self, key_name: str) -> None:
        """Sends a single keypress (down & up) of the specified key."""
        pass

    @abc.abstractmethod
    def press_hotkey(self, keys: List[str]) -> None:
        """Sends a shortcut key combination (modifiers + final key)."""
        pass

    @abc.abstractmethod
    def click_screen(self, x: int, y: int, button: str) -> None:
        """Moves mouse and sends click inputs at the screen coordinates."""
        pass

    @abc.abstractmethod
    def get_screen_dimensions(self) -> Tuple[int, int]:
        """Gets primary monitor virtual resolution width and height."""
        pass

    @abc.abstractmethod
    def is_window_valid(self, hwnd: int) -> bool:
        """Checks if the window handle is alive."""
        pass


class WindowsDesktopBackend(DesktopBackend):
    """Native Windows implementation of DesktopBackend using ctypes Win32 APIs."""

    def get_foreground_window(self) -> Optional[Tuple[int, str, int, str]]:
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if not hwnd:
                return None
            return self._get_window_details(hwnd)
        except Exception as e:
            raise DesktopBackendError(f"Failed to query active foreground window: {e}") from e

    def list_visible_windows(self) -> List[Tuple[int, str, int, str]]:
        windows: List[Tuple[int, str, int, str]] = []

        # WINFUNCTYPE(return_type, *arg_types)
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        def enum_callback(hwnd, lparam):
            try:
                # Top level visible windows only
                if ctypes.windll.user32.IsWindowVisible(hwnd):
                    details = self._get_window_details(hwnd)
                    if details and details[1].strip():
                        windows.append(details)
            except Exception:
                pass  # Ignore invalid handles or permission errors during enum
            return True

        try:
            ctypes.windll.user32.EnumWindows(WNDENUMPROC(enum_callback), 0)
        except Exception as e:
            raise DesktopBackendError(f"Failed to enumerate top-level windows: {e}") from e

        return windows

    def focus_window(self, hwnd: int) -> bool:
        if not self.is_window_valid(hwnd):
            return False

        try:
            # Restore if minimized (SW_RESTORE = 9)
            ctypes.windll.user32.ShowWindow(hwnd, 9)
            time.sleep(0.05)

            # Synthesize ALT down/up to bypass OS SetForegroundWindow restrictions
            ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)  # ALT down
            ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)  # ALT up
            
            success = ctypes.windll.user32.SetForegroundWindow(hwnd)
            time.sleep(0.1)  # Let OS perform window transition
            return bool(success)
        except Exception as e:
            raise DesktopBackendError(f"Failed to set focus to window handle {hwnd}: {e}") from e

    def type_text(self, text: str) -> None:
        try:
            # Send Unicode keystrokes using SendInput
            for char in text:
                # Key Down (KEYEVENTF_UNICODE = 0x0004)
                ki_down = KEYBDINPUT(0, ord(char), 0x0004, 0, 0)
                inp_down = INPUT(1, INPUT_UNION(ki=ki_down))
                ctypes.windll.user32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(INPUT))
                
                # Key Up (KEYEVENTF_UNICODE = 0x0004, KEYEVENTF_KEYUP = 0x0002)
                ki_up = KEYBDINPUT(0, ord(char), 0x0004 | 0x0002, 0, 0)
                inp_up = INPUT(1, INPUT_UNION(ki=ki_up))
                ctypes.windll.user32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(INPUT))
        except Exception as e:
            raise DesktopBackendError(f"Failed typing text sequence: {e}") from e

    def press_key(self, key_name: str) -> None:
        vk = VK_MAP.get(key_name.lower())
        if not vk:
            raise DesktopBackendError(f"Key '{key_name}' cannot be resolved to a Virtual Key code.")

        try:
            # Key Down
            ki_down = KEYBDINPUT(vk, 0, 0, 0, 0)
            inp_down = INPUT(1, INPUT_UNION(ki=ki_down))
            ctypes.windll.user32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(INPUT))

            # Key Up
            ki_up = KEYBDINPUT(vk, 0, 0x0002, 0, 0)
            inp_up = INPUT(1, INPUT_UNION(ki=ki_up))
            ctypes.windll.user32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(INPUT))
        except Exception as e:
            raise DesktopBackendError(f"Failed sending keypress '{key_name}': {e}") from e

    def press_hotkey(self, keys: List[str]) -> None:
        vks = [VK_MAP.get(k.lower()) for k in keys]
        if any(vk is None for vk in vks):
            missing = [keys[i] for i, vk in enumerate(vks) if vk is None]
            raise DesktopBackendError(f"Failed to resolve keys to VK codes: {missing}")

        try:
            # Press modifiers down
            for vk in vks[:-1]:
                ki = KEYBDINPUT(vk, 0, 0, 0, 0)
                inp = INPUT(1, INPUT_UNION(ki=ki))
                ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

            # Press main key down
            ki = KEYBDINPUT(vks[-1], 0, 0, 0, 0)
            inp = INPUT(1, INPUT_UNION(ki=ki))
            ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

            # Press main key up
            ki = KEYBDINPUT(vks[-1], 0, 0x0002, 0, 0)
            inp = INPUT(1, INPUT_UNION(ki=ki))
            ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

            # Press modifiers up (reverse order)
            for vk in reversed(vks[:-1]):
                ki = KEYBDINPUT(vk, 0, 0x0002, 0, 0)
                inp = INPUT(1, INPUT_UNION(ki=ki))
                ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
        except Exception as e:
            raise DesktopBackendError(f"Failed sending hotkey combination {keys}: {e}") from e

    def click_screen(self, x: int, y: int, button: str) -> None:
        btn = button.lower()
        if btn == "left":
            down_flag = 0x0002  # MOUSEEVENTF_LEFTDOWN
            up_flag = 0x0004    # MOUSEEVENTF_LEFTUP
        elif btn == "right":
            down_flag = 0x0008  # MOUSEEVENTF_RIGHTDOWN
            up_flag = 0x0010    # MOUSEEVENTF_RIGHTUP
        else:
            raise DesktopBackendError(f"Unsupported mouse button: '{button}'")

        try:
            # Set cursor pos
            ctypes.windll.user32.SetCursorPos(x, y)
            time.sleep(0.05)  # Tiny pause to let the cursor reposition settle

            # Send clicks
            ctypes.windll.user32.mouse_event(down_flag, 0, 0, 0, 0)
            ctypes.windll.user32.mouse_event(up_flag, 0, 0, 0, 0)
        except Exception as e:
            raise DesktopBackendError(f"Failed sending mouse click at ({x}, {y}): {e}") from e

    def get_screen_dimensions(self) -> Tuple[int, int]:
        try:
            cx = ctypes.windll.user32.GetSystemMetrics(0)  # SM_CXSCREEN
            cy = ctypes.windll.user32.GetSystemMetrics(1)  # SM_CYSCREEN
            if cx > 0 and cy > 0:
                return cx, cy
            return 1920, 1080  # Fallback for headless environments
        except Exception:
            return 1920, 1080

    def is_window_valid(self, hwnd: int) -> bool:
        try:
            return bool(ctypes.windll.user32.IsWindow(hwnd))
        except Exception:
            return False

    def _get_window_details(self, hwnd: int) -> Optional[Tuple[int, str, int, str]]:
        if not self.is_window_valid(hwnd):
            return None

        # 1. Title
        title_len = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        if title_len > 0:
            buf = ctypes.create_unicode_buffer(title_len + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, title_len + 1)
            title = buf.value
        else:
            title = ""

        # 2. Process ID
        pid = ctypes.c_ulong()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        pid_val = pid.value

        # 3. Process Name
        process_name = ""
        if pid_val > 0:
            try:
                process_name = psutil.Process(pid_val).name()
            except Exception:
                process_name = "unknown"

        return hwnd, title, pid_val, process_name
