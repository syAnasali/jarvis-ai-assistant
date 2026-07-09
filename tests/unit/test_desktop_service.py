"""Unit tests for the Desktop Interaction Subsystem (models, policy, resolver, service, and tools)."""

import pytest
import os
import tempfile
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType

from app.services.desktop.models import DesktopWindow, DesktopMetrics
from app.services.desktop.policy import DesktopPolicy
from app.services.desktop.resolver import DesktopResolver, ResolutionStatus, ResolutionResult
from app.services.desktop.backend import DesktopBackend
from app.services.desktop.service import DesktopService
from app.core.exceptions import (
    DesktopError,
    WindowNotFoundError,
    WindowAmbiguousError,
    WindowStaleError,
    WindowNotVisibleError,
    FocusFailedError,
    ForegroundChangedError,
    InvalidTextError,
    TextTooLongError,
    InvalidKeyError,
    InvalidHotkeyError,
    InvalidCoordinatesError,
    UnsupportedButtonError,
)
from app.tools.models import ToolPermission, ToolResult
from app.agent.models import ToolCall
from app.tools.registry import ToolRegistry
from app.tools.executor import ToolExecutor
from app.approval.repository import SQLiteApprovalRepository
from app.approval.manager import ApprovalManager
from app.approval.models import PendingActionStatus, PendingAction

from app.tools.builtin.desktop import (
    GetActiveWindowTool,
    ListVisibleWindowsTool,
    FocusWindowTool,
    TypeTextTool,
    PressKeyTool,
    PressHotkeyTool,
    ClickScreenTool,
)


class FakeDesktopBackend(DesktopBackend):
    """Mocks win32 desktop interactions for consistent unit test execution."""

    def __init__(self) -> None:
        self.windows = []  # List of Tuple[hwnd, title, pid, process_name]
        self.active_hwnd = 0
        self.cursor_pos = (0, 0)
        self.typed_text = []
        self.pressed_keys = []
        self.pressed_hotkeys = []
        self.clicks = []
        self.screen_dims = (1920, 1080)
        self.valid_hwnds = set()

    def get_foreground_window(self):
        for w in self.windows:
            if w[0] == self.active_hwnd:
                return w
        return None

    def list_visible_windows(self):
        return [w for w in self.windows if w[0] in self.valid_hwnds]

    def focus_window(self, hwnd):
        if hwnd in self.valid_hwnds:
            self.active_hwnd = hwnd
            return True
        return False

    def type_text(self, text):
        self.typed_text.append(text)

    def press_key(self, key_name):
        self.pressed_keys.append(key_name)

    def press_hotkey(self, keys):
        self.pressed_hotkeys.append(keys)

    def click_screen(self, x, y, button):
        self.cursor_pos = (x, y)
        self.clicks.append((x, y, button))

    def get_screen_dimensions(self):
        return self.screen_dims

    def is_window_valid(self, hwnd):
        return hwnd in self.valid_hwnds


# =====================================================================
# WINDOW DOMAIN MODEL TESTS
# =====================================================================

def test_window_model_immutability():
    """Verify DesktopWindow fields are immutable and metadata defensively copied."""
    meta = {"hwnd": 1234, "custom": "field"}
    win = DesktopWindow(
        window_id="win_a1b2c3d4",
        title="Notepad",
        process_id=9876,
        process_name="notepad.exe",
        is_visible=True,
        is_foreground=False,
        metadata=meta
    )

    assert win.window_id == "win_a1b2c3d4"
    assert win.title == "Notepad"
    assert win.process_id == 9876
    assert win.process_name == "notepad.exe"
    assert win.is_visible is True
    assert win.is_foreground is False
    assert isinstance(win.metadata, MappingProxyType)
    assert win.metadata["hwnd"] == 1234

    # Test frozen/immutability
    with pytest.raises(Exception):
        win.title = "Other"

    # Test metadata edit rejection
    with pytest.raises(TypeError):
        win.metadata["new"] = "value"


# =====================================================================
# DESKTOP POLICY TESTS
# =====================================================================

def test_policy_text_validation():
    """Verify policy rejects NUL bytes and size limits."""
    policy = DesktopPolicy()
    
    # Valid text
    policy.validate_text("Hello Anas", max_chars=100)

    # NUL byte rejection
    with pytest.raises(InvalidTextError, match="NUL bytes"):
        policy.validate_text("Hello\x00Anas", max_chars=100)

    # Size limit
    with pytest.raises(TextTooLongError, match="exceeds maximum"):
        policy.validate_text("A" * 101, max_chars=100)


def test_policy_key_validation():
    """Verify policy key checks allowed keys and invalid configurations."""
    policy = DesktopPolicy()

    # Allowed keys
    policy.validate_key("enter")
    policy.validate_key("ESCAPE")

    # Invalid key
    with pytest.raises(InvalidKeyError):
        policy.validate_key("f1")
    with pytest.raises(InvalidKeyError):
        policy.validate_key("alt")


def test_policy_hotkey_canonicalization():
    """Verify policy canonicalizes combinations and enforces combinations allowlist."""
    policy = DesktopPolicy()

    # Valid canonicalization
    assert policy.canonicalize_hotkey("ctrl+c") == ["ctrl", "c"]
    assert policy.canonicalize_hotkey("Control+S") == ["ctrl", "s"]
    assert policy.canonicalize_hotkey(["CTRL", "a"]) == ["ctrl", "a"]

    # Duplicate keys
    with pytest.raises(InvalidHotkeyError, match="Duplicate keys"):
        policy.canonicalize_hotkey("ctrl+ctrl+c")

    # Blocked hotkey combination
    with pytest.raises(InvalidHotkeyError, match="not permitted"):
        policy.canonicalize_hotkey("ctrl+alt+delete")
    with pytest.raises(InvalidHotkeyError, match="not permitted"):
        policy.canonicalize_hotkey("win+r")


def test_policy_coordinates_validation():
    """Verify policy rejects negative or out-of-bounds coordinates."""
    policy = DesktopPolicy()

    # Valid
    policy.validate_coordinates(100, 200, 1920, 1080)

    # Negative coordinates
    with pytest.raises(InvalidCoordinatesError, match="cannot be negative"):
        policy.validate_coordinates(-10, 100, 1920, 1080)

    # Out of bounds
    with pytest.raises(InvalidCoordinatesError, match="outside the current virtual screen"):
        policy.validate_coordinates(1920, 1000, 1920, 1080)
    with pytest.raises(InvalidCoordinatesError, match="outside the current virtual screen"):
        policy.validate_coordinates(500, 1081, 1920, 1080)


def test_policy_button_validation():
    """Verify policy only accepts left and right buttons."""
    policy = DesktopPolicy()

    assert policy.validate_button("left") == "left"
    assert policy.validate_button(" RIGHT ") == "right"

    with pytest.raises(UnsupportedButtonError):
        policy.validate_button("middle")


# =====================================================================
# WINDOW RESOLUTION TESTS
# =====================================================================

def test_resolver_match_ranking():
    """Verify resolver ranks matches: exact title > exact process > prefix > substring."""
    resolver = DesktopResolver()
    
    windows = [
        DesktopWindow("w1", "My Notepad Document", 101, "notepad.exe", True, False),
        DesktopWindow("w2", "Google Chrome", 102, "chrome.exe", True, False),
        DesktopWindow("w3", "Notepad", 103, "notepad.exe", True, False),
        DesktopWindow("w4", "Visual Studio Code - Workspace", 104, "code.exe", True, False),
    ]

    # Exact Title Match
    res1 = resolver.resolve("Notepad", windows)
    assert res1.status == ResolutionStatus.RESOLVED
    assert res1.window.window_id == "w3"

    # Exact Process Match (ignoring case/.exe)
    res2 = resolver.resolve("chrome", windows)
    assert res2.status == ResolutionStatus.RESOLVED
    assert res2.window.window_id == "w2"

    # Prefix Title Match
    res3 = resolver.resolve("Visual Studio", windows)
    assert res3.status == ResolutionStatus.RESOLVED
    assert res3.window.window_id == "w4"

    # Substring Title Match
    res4 = resolver.resolve("Document", windows)
    assert res4.status == ResolutionStatus.RESOLVED
    assert res4.window.window_id == "w1"

    # Not found
    res5 = resolver.resolve("UnknownApp", windows)
    assert res5.status == ResolutionStatus.NOT_FOUND


def test_resolver_ambiguity():
    """Verify resolver returns AMBIGUOUS if multiple matches exist at same rank."""
    resolver = DesktopResolver()
    
    windows = [
        DesktopWindow("w1", "Notepad Document A", 101, "notepad.exe", True, False),
        DesktopWindow("w2", "Notepad Document B", 102, "notepad.exe", True, False),
    ]

    # Prefix match "Notepad" matches both w1 and w2
    res = resolver.resolve("Notepad", windows)
    assert res.status == ResolutionStatus.AMBIGUOUS
    assert len(res.candidates) == 2
    assert res.candidates[0].window_id == "w1"
    assert res.candidates[1].window_id == "w2"


# =====================================================================
# WINDOW REGISTRY & SERVICE TESTS
# =====================================================================

@pytest.fixture
def fake_backend() -> FakeDesktopBackend:
    backend = FakeDesktopBackend()
    # Register window handles
    backend.windows = [
        (1001, "Notepad", 9001, "notepad.exe"),
        (1002, "Google Chrome", 9002, "chrome.exe"),
        (1003, "Jarvis Assistant", os.getpid(), "python.exe"),  # Excluded Jarvis process
    ]
    backend.valid_hwnds = {1001, 1002, 1003}
    backend.active_hwnd = 1001
    return backend


@pytest.fixture
def desktop_service(fake_backend) -> DesktopService:
    policy = DesktopPolicy()
    resolver = DesktopResolver()
    return DesktopService(policy, resolver, fake_backend, list_limit=10)


def test_service_get_active_window(desktop_service):
    """Verify active window resolution, stable ID mapping, and native handle hiding."""
    win = desktop_service.get_active_window()
    assert win.title == "Notepad"
    assert win.process_name == "notepad.exe"
    assert win.is_foreground is True
    
    # Stable runtime ID generated
    assert win.window_id.startswith("win_")
    
    # Check that native handle is registered but not exposed on properties
    hwnd = desktop_service._id_to_hwnd.get(win.window_id)
    assert hwnd == 1001


def test_service_list_visible_windows_exclusion_and_sorting(desktop_service):
    """Verify invisible/stale/Jarvis process exclusions and deterministic sorting."""
    # List windows
    visible = desktop_service.list_visible_windows()
    
    # Jarvis process (python.exe with my_pid) must be excluded
    titles = [w.title for w in visible]
    assert "Jarvis Assistant" not in titles
    assert "Notepad" in titles
    assert "Google Chrome" in titles

    # List is sorted alphabetically by title ("Google Chrome" before "Notepad")
    assert visible[0].title == "Google Chrome"
    assert visible[1].title == "Notepad"


def test_service_focus_window_verification(desktop_service, fake_backend):
    """Verify window focus switches and verifies foreground state."""
    visible = desktop_service.list_visible_windows()
    notepad_win = [w for w in visible if w.title == "Notepad"][0]
    chrome_win = [w for w in visible if w.title == "Google Chrome"][0]

    # Switch focus from Notepad (1001) to Chrome (1002)
    assert fake_backend.active_hwnd == 1001
    desktop_service.focus_window(chrome_win.window_id)
    assert fake_backend.active_hwnd == 1002

    # Attempting to focus a stale ID raises WindowNotFoundError
    with pytest.raises(WindowNotFoundError):
        desktop_service.focus_window("win_dead1234")

    # Attempting to focus a dead handle raises WindowStaleError
    fake_backend.valid_hwnds.remove(1001)  # Notepad closed
    with pytest.raises(WindowStaleError):
        desktop_service.focus_window(notepad_win.window_id)


def test_service_wait_for_window_timeout(desktop_service):
    """Verify wait_for_window resolves window or times out."""
    # Resolves notepad immediately
    win = desktop_service.wait_for_window("Notepad", timeout_seconds=1.0)
    assert win.title == "Notepad"

    # Times out on non-existent window
    with pytest.raises(WindowNotFoundError, match="was not found within"):
        desktop_service.wait_for_window("NonExistent", timeout_seconds=0.2, poll_interval_ms=50)


# =====================================================================
# FOREGROUND GUARD & MUTATION TESTS
# =====================================================================

def test_foreground_safety_guard(desktop_service, fake_backend):
    """Verify mutations execute when foreground is unchanged, and block when changed."""
    active_win = desktop_service.get_active_window()
    assert active_win.title == "Notepad"

    # 1. Unchanged target: executes successfully
    desktop_service.type_text("Hello World", expected_foreground_id=active_win.window_id)
    assert fake_backend.typed_text[-1] == "Hello World"

    # 2. Changed target: blocks execution and raises ForegroundChangedError
    fake_backend.active_hwnd = 1002  # User switched focus to Chrome
    with pytest.raises(ForegroundChangedError, match="Active focus switched"):
        desktop_service.type_text("Typing text in wrong window", expected_foreground_id=active_win.window_id)
    
    # Keystrokes were NOT sent to the backend
    assert fake_backend.typed_text[-1] == "Hello World"


def test_press_key_safety(desktop_service, fake_backend):
    """Verify press_key enforces key allowlist and foreground checks."""
    active_win = desktop_service.get_active_window()
    
    # Valid key
    desktop_service.press_key("enter", expected_foreground_id=active_win.window_id)
    assert fake_backend.pressed_keys[-1] == "enter"

    # Invalid key
    with pytest.raises(InvalidKeyError):
        desktop_service.press_key("win", expected_foreground_id=active_win.window_id)


def test_press_hotkey_safety(desktop_service, fake_backend):
    """Verify press_hotkey combination checks and foreground guards."""
    active_win = desktop_service.get_active_window()

    # Valid canonical shortcut
    desktop_service.press_hotkey(["ctrl", "s"], expected_foreground_id=active_win.window_id)
    assert fake_backend.pressed_hotkeys[-1] == ["ctrl", "s"]

    # Blocked combination
    with pytest.raises(InvalidHotkeyError):
        desktop_service.press_hotkey(["win", "e"], expected_foreground_id=active_win.window_id)


def test_click_screen_bounds_and_safety(desktop_service, fake_backend):
    """Verify click_screen bounds checking and foreground guard."""
    active_win = desktop_service.get_active_window()

    # Valid
    desktop_service.click_screen(500, 500, "left", expected_foreground_id=active_win.window_id)
    assert fake_backend.clicks[-1] == (500, 500, "left")

    # Invalid coordinates (outside 1920x1080 screen)
    with pytest.raises(InvalidCoordinatesError):
        desktop_service.click_screen(2000, 500, "left", expected_foreground_id=active_win.window_id)


# =====================================================================
# APPROVAL INTEGRATION TESTS
# =====================================================================

@pytest.fixture
def approval_integration(desktop_service) -> Tuple[ToolRegistry, ToolExecutor, ApprovalManager, Path]:
    # Set up SQLite repository
    temp_dir = tempfile.mkdtemp()
    db_file = Path(temp_dir) / "test_approval.db"
    repo = SQLiteApprovalRepository(database_path=db_file)
    manager = ApprovalManager(repository=repo, timeout_seconds=10)

    registry = ToolRegistry()
    registry.register(TypeTextTool(desktop_service, manager))
    executor = ToolExecutor(registry, manager)

    return registry, executor, manager, db_file


def test_approval_integration_type_text_flow(desktop_service, fake_backend, approval_integration):
    """Verify approval lifecycle: suspension, rejection, expiration, replay, success."""
    registry, executor, manager, db_file = approval_integration
    active_win = desktop_service.get_active_window()

    tc = ToolCall(tool_name="type_text", arguments={"text": "Confidential Message"})

    # 1. No input executed before approval
    res1 = executor.execute(tc)
    assert res1.success is False
    assert res1.metadata.get("confirmation_required") is True
    pending_id = res1.metadata.get("pending_action_id")
    assert pending_id is not None
    assert not fake_backend.typed_text

    # 2. Rejection blocks execution
    manager.reject(pending_id)
    res_rej = executor.execute(tc, approval_action_id=pending_id)
    assert res_rej.success is False
    assert "REJECTED" in res_rej.error
    assert not fake_backend.typed_text

    # 3. Expiration blocks execution
    res2 = executor.execute(tc)
    pending_id2 = res2.metadata.get("pending_action_id")
    manager._repository.update_status(pending_id2, PendingActionStatus.EXPIRED)
    res_exp = executor.execute(tc, approval_action_id=pending_id2)
    assert res_exp.success is False
    assert "EXPIRED" in res_exp.error

    # 4. Success executing approved action
    res3 = executor.execute(tc)
    pending_id3 = res3.metadata.get("pending_action_id")
    manager.approve(pending_id3)
    
    res_exec = executor.execute(tc, approval_action_id=pending_id3)
    assert res_exec.success is True
    assert fake_backend.typed_text[-1] == "Confidential Message"

    # 5. Replay blocks duplicate execution
    res_rep = executor.execute(tc, approval_action_id=pending_id3)
    assert res_rep.success is False
    assert "Replay blocked" in res_rep.error

    # Cleanup SQLite DB file
    try:
        os.remove(db_file)
        os.rmdir(db_file.parent)
    except Exception:
        pass
