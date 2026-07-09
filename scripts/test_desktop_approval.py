"""Diagnostic script to verify desktop interaction approval flows and foreground window safety checks."""

import os
import sys
import tempfile
import shutil
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.desktop.policy import DesktopPolicy
from app.services.desktop.resolver import DesktopResolver
from app.services.desktop.service import DesktopService
from app.tools.builtin.desktop import TypeTextTool
from app.tools.registry import ToolRegistry
from app.tools.executor import ToolExecutor
from app.agent.models import ToolCall
from app.approval.repository import SQLiteApprovalRepository
from app.approval.manager import ApprovalManager
from app.core.exceptions import ForegroundChangedError

from tests.unit.test_desktop_service import FakeDesktopBackend


def run_diagnostics() -> bool:
    print("=== Running Desktop Action Approval & Foreground Guard Diagnostics ===")
    
    success = True
    temp_dir = Path(tempfile.mkdtemp())
    try:
        # 1. Setup SQLite Database Approval Repository and ApprovalManager
        db_file = temp_dir / "test_approval.db"
        repo = SQLiteApprovalRepository(database_path=db_file)
        manager = ApprovalManager(repository=repo, timeout_seconds=10)

        # 2. Setup Desktop service with Fake backend
        fake_backend = FakeDesktopBackend()
        fake_backend.windows = [
            (1001, "Notepad", 5001, "notepad.exe"),
            (1002, "Google Chrome", 5002, "chrome.exe"),
        ]
        fake_backend.valid_hwnds = {1001, 1002}
        fake_backend.active_hwnd = 1001  # Notepad starts active

        policy = DesktopPolicy()
        resolver = DesktopResolver()
        service = DesktopService(policy, resolver, fake_backend)

        # 3. Setup ToolExecutor
        registry = ToolRegistry()
        registry.register(TypeTextTool(service, manager))
        executor = ToolExecutor(registry, manager)

        # 4. Trigger typing action tool call
        print("\nPart 1: Triggering Type Text tool call (requires confirmation)...")
        tc = ToolCall(tool_name="type_text", arguments={"text": "Hello Anas"})
        res1 = executor.execute(tc)
        
        if res1.success is False and res1.metadata.get("confirmation_required") is True:
            print("  [PASS] Tool call correctly suspended on confirmation.")
        else:
            print(f"  [FAIL] Tool call was not suspended correctly: {res1}")
            success = False

        pending_id = res1.metadata.get("pending_action_id")
        action = manager.get(pending_id)
        
        # Check target identity is frozen in metadata
        target_id = action.metadata.get("expected_foreground_window_id")
        target_title = action.metadata.get("expected_foreground_window_title")
        if target_title == "Notepad":
            print(f"  [PASS] Target window identity frozen in PendingAction metadata: ID={target_id} Title='{target_title}'")
        else:
            print(f"  [FAIL] Target window not frozen correctly in metadata: {action.metadata}")
            success = False

        # 5. Approve the action
        manager.approve(pending_id)
        print("  Pending action approved in database.")

        # 6. Test Foreground safety guard: mismatch HWND
        print("\nPart 2: Simulating user window focus change before execution...")
        # User switched focus to Chrome
        fake_backend.active_hwnd = 1002
        
        res_fail = executor.execute(tc, approval_action_id=pending_id)
        if res_fail.success is False and "Foreground safety guard" in res_fail.error:
            print("  [PASS] Execution correctly blocked because the active window changed.")
            print(f"         Error message: {res_fail.error}")
        else:
            print(f"  [FAIL] Execution was not blocked. Res: {res_fail}")
            success = False

        # Check metrics
        if service.metrics.foreground_change_blocks == 1:
            print("  [PASS] Metrics counter 'foreground_change_blocks' incremented.")
        else:
            print(f"  [FAIL] Metrics not incremented. Metrics: {service.metrics.to_dict()}")
            success = False

        # 7. Test Foreground safety guard: matching HWND (restore focus to notepad)
        print("\nPart 3: Restoring window focus and executing with a new approved action...")
        fake_backend.active_hwnd = 1001
        
        # Re-trigger tool call
        res3 = executor.execute(tc)
        new_pending_id = res3.metadata.get("pending_action_id")
        manager.approve(new_pending_id)
        
        # Execute approved action
        res_ok = executor.execute(tc, approval_action_id=new_pending_id)
        if res_ok.success is True:
            print("  [PASS] Execution succeeded with active window matching the target.")
            print(f"         Backend typed text: '{fake_backend.typed_text[-1]}'")
        else:
            print(f"  [FAIL] Approved execution failed: {res_ok.error}")
            success = False

    finally:
        shutil.rmtree(temp_dir)

    print("\n==========================================================")
    if success:
        print("DIAGNOSTICS STATUS: PASS")
    else:
        print("DIAGNOSTICS STATUS: FAIL")
    print("==========================================================")
    return success


if __name__ == "__main__":
    ok = run_diagnostics()
    sys.exit(0 if ok else 1)
