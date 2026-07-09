"""Diagnostic script for Action Rejection."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.core.application import Application
from app.agent.models import ToolCall
from app.approval.models import PendingActionStatus
from tests.unit.test_approval_system import RecordConfirmationActionTool


def run_diagnostic():
    print("=== Action Rejection Diagnostic ===")
    
    app = Application()
    try:
        app.initialize()
        app._initialize_llm()
        app._initialize_agent()
    except Exception as e:
        print(f"FAILED: Application initialization failed: {e}")
        sys.exit(1)

    registry = app.container.get("tool_registry")
    recorder = []
    conf_tool = RecordConfirmationActionTool(recorder)
    registry.register(conf_tool)

    executor = app.container.get("tool_executor")
    manager = app.container.get("approval_manager")

    failures = 0

    # 1. Request action
    print("\n1. Requesting action requiring confirmation...")
    tc = ToolCall(tool_name="record_confirmation_action", arguments={"value": "rejection_test"})
    res = executor.execute(tc)
    
    if not res.success and res.metadata.get("confirmation_required") is True:
        action_id = res.metadata.get("pending_action_id")
        print(f"  [PASS] PendingAction created: ID={action_id}")
    else:
        print("  [FAIL] Expected confirmation_required tool result.")
        failures += 1
        return

    # 2. Reject
    print("\n2. Rejecting action...")
    try:
        manager.reject(action_id)
        action = manager.get(action_id)
        if action.status == PendingActionStatus.REJECTED:
            print("  [PASS] Action status updated to REJECTED.")
        else:
            print(f"  [FAIL] Action status was {action.status.value}")
            failures += 1
    except Exception as e:
        print(f"  [FAIL] Failed to reject action: {e}")
        failures += 1

    # 3. Verify execution blocked
    print("\n3. Verifying execution blocked...")
    res_exec = executor.execute(tc, approval_action_id=action_id)
    if not res_exec.success and "REJECTED" in res_exec.error:
        print("  [PASS] Execution of rejected action successfully blocked.")
    else:
        print(f"  [FAIL] Expected execution to be blocked, but got: {res_exec.error if not res_exec.success else 'success'}")
        failures += 1

    # Verify tool never ran
    if len(recorder) == 0:
        print("  [PASS] Tool has not executed.")
    else:
        print("  [FAIL] Tool executed despite rejection.")
        failures += 1

    print("\n-------------------------------------------")
    if failures == 0:
        print("DIAGNOSTIC STATUS: PASS")
    else:
        print(f"DIAGNOSTIC STATUS: FAIL ({failures} failures)")
        sys.exit(1)


if __name__ == "__main__":
    run_diagnostic()
