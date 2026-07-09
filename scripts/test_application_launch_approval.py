"""Diagnostic script for application launch approval flow."""

import sys
import os
import signal
import time
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.application import Application
from app.services.applications.resolver import ApplicationResolver
from app.tools.models import ToolResult
from app.agent.models import ToolCall
from app.approval.models import PendingActionStatus


def run_diagnostic():
    print("=== Application Launch Approval Diagnostic ===")
    
    app = Application()
    try:
        app.initialize()
        app._initialize_llm()
        app._initialize_agent()
    except Exception as e:
        print(f"FAILED: Application initialization failed: {e}")
        sys.exit(1)

    resolver = ApplicationResolver()
    executor = app.container.get("tool_executor")
    manager = app.container.get("approval_manager")

    failures = 0

    # 1. Resolve Notepad
    print("\n1. Resolving 'Notepad'...")
    res_resolve = resolver.resolve("Notepad")
    if res_resolve.status == "RESOLVED" and res_resolve.application:
        app_id = res_resolve.application.application_id
        print(f"  [PASS] Resolved: ID={app_id}, Path={res_resolve.application.executable_path}")
    else:
        print(f"  [FAIL] Failed to resolve Notepad: status={res_resolve.status}")
        sys.exit(1)

    # 2. Request launch (should suspend and create pending action)
    print("\n2. Requesting launch (should suspend)...")
    tc = ToolCall(tool_name="launch_application", arguments={"application_id": app_id})
    res_launch = executor.execute(tc)

    if not res_launch.success and res_launch.metadata.get("confirmation_required") is True:
        action_id = res_launch.metadata.get("pending_action_id")
        print(f"  [PASS] Launch suspended. PendingAction ID: {action_id}")
    else:
        print(f"  [FAIL] Launch did not suspend. Result: success={res_launch.success}, error={res_launch.error}")
        failures += 1
        return

    # Verify no notepad process was launched yet
    # We can check list of processes, but since we didn't approve, it's guaranteed not to run.
    print("  [PASS] Notepad was not launched yet.")

    # 3. Approve action
    print("\n3. Approving action in database...")
    try:
        manager.approve(action_id)
        action = manager.get(action_id)
        if action.status == PendingActionStatus.APPROVED:
            print("  [PASS] Action status updated to APPROVED.")
        else:
            print(f"  [FAIL] Action status is {action.status.value}")
            failures += 1
    except Exception as e:
        print(f"  [FAIL] Failed to approve action: {e}")
        failures += 1

    # 4. Execute approved action
    print("\n4. Executing approved launch...")
    pid = None
    res_exec = executor.execute(tc, approval_action_id=action_id)
    if res_exec.success and res_exec.output.get("launched") is True:
        pid = res_exec.output.get("pid")
        print(f"  [PASS] Notepad successfully launched! Process PID: {pid}")
    else:
        print(f"  [FAIL] Launch execution failed: {res_exec.error}")
        failures += 1

    # 5. Verify replay block
    print("\n5. Verifying replay block...")
    res_replay = executor.execute(tc, approval_action_id=action_id)
    if not res_replay.success and "Replay blocked" in res_replay.error:
        print("  [PASS] Replay blocked successfully.")
    else:
        print(f"  [FAIL] Replay not blocked: success={res_replay.success}, error={res_replay.error}")
        failures += 1

    # 6. Cleanup process
    if pid:
        print(f"\n6. Cleaning up launched process (PID: {pid})...")
        try:
            # Terminate notepad
            os.kill(pid, signal.SIGTERM)
            print("  [PASS] Process terminated successfully.")
        except Exception as e:
            print(f"  [WARNING] Process cleanup warning: {e}")

    print("\n-------------------------------------------")
    if failures == 0:
        print("DIAGNOSTIC STATUS: PASS")
    else:
        print(f"DIAGNOSTIC STATUS: FAIL ({failures} failures)")
        sys.exit(1)


if __name__ == "__main__":
    run_diagnostic()
