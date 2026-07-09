"""Diagnostic script for Action Approval Lifecycle."""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.application import Application
from app.tools.registry import ToolRegistry
from app.tools.executor import ToolExecutor
from app.tools.models import ToolPermission
from app.agent.models import ToolCall
from app.approval.models import PendingActionStatus
from tests.unit.test_approval_system import RecordConfirmationActionTool


def run_diagnostic():
    print("=== Action Approval Lifecycle Diagnostic ===")
    
    app = Application()
    try:
        app.initialize()
        app._initialize_llm()
        app._initialize_agent()
    except Exception as e:
        print(f"FAILED: Application initialization failed: {e}")
        sys.exit(1)

    # Setup diagnostic tool and repository
    registry = app.container.get("tool_registry")
    recorder = []
    conf_tool = RecordConfirmationActionTool(recorder)
    registry.register(conf_tool)

    executor = app.container.get("tool_executor")
    manager = app.container.get("approval_manager")

    failures = 0

    # 1. Request action
    print("\n1. Requesting action requiring confirmation...")
    tc = ToolCall(tool_name="record_confirmation_action", arguments={"value": "lifecycle_test"})
    res = executor.execute(tc)
    
    if not res.success and res.metadata.get("confirmation_required") is True:
        action_id = res.metadata.get("pending_action_id")
        print(f"  [PASS] PendingAction created: ID={action_id}")
    else:
        print("  [FAIL] Expected confirmation_required tool result.")
        failures += 1
        return

    # Verify tool NOT executed
    if len(recorder) == 0:
        print("  [PASS] Tool has not executed yet.")
    else:
        print("  [FAIL] Tool executed prematurely.")
        failures += 1

    # 2. Approve
    print("\n2. Approving action...")
    try:
        manager.approve(action_id)
        action = manager.get(action_id)
        if action.status == PendingActionStatus.APPROVED:
            print("  [PASS] Action status updated to APPROVED.")
        else:
            print(f"  [FAIL] Action status was {action.status.value}")
            failures += 1
    except Exception as e:
        print(f"  [FAIL] Failed to approve action: {e}")
        failures += 1

    # 3. Execute approved action
    print("\n3. Executing approved action...")
    res_exec = executor.execute(tc, approval_action_id=action_id)
    if res_exec.success:
        print(f"  [PASS] Action executed successfully. Output: {res_exec.output}")
    else:
        print(f"  [FAIL] Failed to execute action: {res_exec.error}")
        failures += 1

    # Verify tool executed exactly once
    if len(recorder) == 1 and recorder[0] == "lifecycle_test":
        print("  [PASS] Tool executed exactly once with correct value.")
    else:
        print(f"  [FAIL] Tool execution count is {len(recorder)} instead of 1.")
        failures += 1

    # 4. Replay block
    print("\n4. Verifying replay block...")
    res_replay = executor.execute(tc, approval_action_id=action_id)
    if not res_replay.success and "Replay blocked" in res_replay.error:
        print("  [PASS] Replay blocked successfully.")
    else:
        print(f"  [FAIL] Expected replay to be blocked, but got: {res_replay.error if not res_replay.success else 'success'}")
        failures += 1

    print("\n-------------------------------------------")
    if failures == 0:
        print("DIAGNOSTIC STATUS: PASS")
    else:
        print(f"DIAGNOSTIC STATUS: FAIL ({failures} failures)")
        sys.exit(1)


if __name__ == "__main__":
    run_diagnostic()
