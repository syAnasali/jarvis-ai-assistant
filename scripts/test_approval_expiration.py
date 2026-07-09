"""Diagnostic script for Action Expiration."""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.append(str(Path(__file__).parent.parent))

from app.core.application import Application
from app.agent.models import ToolCall
from app.approval.models import PendingActionStatus
from tests.unit.test_approval_system import RecordConfirmationActionTool


def run_diagnostic():
    print("=== Action Expiration Diagnostic ===")
    
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
    db_path = app.container.get("approval_repository")._db_path

    failures = 0

    # 1. Request action
    print("\n1. Requesting action requiring confirmation...")
    tc = ToolCall(tool_name="record_confirmation_action", arguments={"value": "expiration_test"})
    res = executor.execute(tc)
    
    if not res.success and res.metadata.get("confirmation_required") is True:
        action_id = res.metadata.get("pending_action_id")
        print(f"  [PASS] PendingAction created: ID={action_id}")
    else:
        print("  [FAIL] Expected confirmation_required tool result.")
        failures += 1
        return

    # 2. Force expiration in Database
    print("\n2. Simulating timeout by modifying database record...")
    try:
        conn = sqlite3.connect(str(db_path))
        past_time = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
        conn.execute("UPDATE pending_actions SET expires_at = ? WHERE action_id = ?", (past_time, action_id))
        conn.commit()
        conn.close()
        print("  [PASS] Database updated with past expiration timestamp.")
    except Exception as e:
        print(f"  [FAIL] Database update failed: {e}")
        failures += 1
        return

    # 3. Try to approve expired action
    print("\n3. Attempting to approve expired action...")
    try:
        manager.approve(action_id)
        print("  [FAIL] Approval of expired action succeeded (should fail).")
        failures += 1
    except Exception as e:
        print(f"  [PASS] Approval blocked correctly: {e}")

    # 4. Try to execute expired action
    print("\n4. Attempting to execute expired action...")
    res_exec = executor.execute(tc, approval_action_id=action_id)
    if not res_exec.success and "EXPIRED" in res_exec.error:
        print("  [PASS] Execution blocked correctly.")
    else:
        print(f"  [FAIL] Expected execution to be blocked, got success={res_exec.success}")
        failures += 1

    print("\n-------------------------------------------")
    if failures == 0:
        print("DIAGNOSTIC STATUS: PASS")
    else:
        print(f"DIAGNOSTIC STATUS: FAIL ({failures} failures)")
        sys.exit(1)


if __name__ == "__main__":
    run_diagnostic()
