"""Diagnostic script for Action Approval persistence across process restarts."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.core.application import Application
from app.agent.models import ToolCall
from app.tools.registry import ToolRegistry
from app.tools.executor import ToolExecutor
from app.approval.repository import SQLiteApprovalRepository
from app.approval.manager import ApprovalManager
from tests.unit.test_approval_system import RecordConfirmationActionTool


def run_diagnostic():
    print("=== Action Approval Restart/Persistence Diagnostic ===")
    
    app = Application()
    try:
        app.initialize()
        app._initialize_llm()
        app._initialize_agent()
    except Exception as e:
        print(f"FAILED: Application initialization failed: {e}")
        sys.exit(1)

    db_path = app.container.get("approval_repository")._db_path
    failures = 0

    # ----------------------------------------------------
    # Phase 1: Create, approve, and destroy
    # ----------------------------------------------------
    print("\n--- Phase 1: Creating and approving action ---")
    
    # 1. Setup Phase 1 components
    registry1 = ToolRegistry()
    recorder1 = []
    conf_tool1 = RecordConfirmationActionTool(recorder1)
    registry1.register(conf_tool1)

    repo1 = SQLiteApprovalRepository(database_path=db_path)
    manager1 = ApprovalManager(repository=repo1)
    executor1 = ToolExecutor(registry1, approval_manager=manager1)

    # 2. Request action
    tc = ToolCall(tool_name="record_confirmation_action", arguments={"value": "restart_persistence_test"})
    res1 = executor1.execute(tc)
    if not res1.success and res1.metadata.get("confirmation_required") is True:
        action_id = res1.metadata.get("pending_action_id")
        print(f"  [PASS] Action created: ID={action_id}")
    else:
        print("  [FAIL] Failed to create pending action in Phase 1.")
        failures += 1
        return

    # 3. Approve action
    try:
        manager1.approve(action_id)
        print("  [PASS] Action approved in Phase 1.")
    except Exception as e:
        print(f"  [FAIL] Failed to approve action in Phase 1: {e}")
        failures += 1
        return

    # 4. Destroy Phase 1 objects
    print("  Destroying Phase 1 repository and manager objects...")
    del executor1
    del manager1
    del repo1

    # ----------------------------------------------------
    # Phase 2: Reconstruct, consume, verify replay blocked
    # ----------------------------------------------------
    print("\n--- Phase 2: Reconstructing and executing ---")
    
    # 1. Setup Phase 2 components
    registry2 = ToolRegistry()
    recorder2 = []
    conf_tool2 = RecordConfirmationActionTool(recorder2)
    registry2.register(conf_tool2)

    repo2 = SQLiteApprovalRepository(database_path=db_path)
    manager2 = ApprovalManager(repository=repo2)
    executor2 = ToolExecutor(registry2, approval_manager=manager2)

    # 2. Consume and execute
    print("  Executing approved action using reconstructed objects...")
    res2 = executor2.execute(tc, approval_action_id=action_id)
    if res2.success:
        print(f"  [PASS] Action executed successfully in Phase 2. Output: {res2.output}")
    else:
        print(f"  [FAIL] Failed to execute action in Phase 2: {res2.error}")
        failures += 1

    # Verify tool executed exactly once
    if len(recorder2) == 1 and recorder2[0] == "restart_persistence_test":
        print("  [PASS] Reconstructed tool execution succeeded.")
    else:
        print(f"  [FAIL] Execution list count: {len(recorder2)}")
        failures += 1

    # 3. Verify replay blocked
    print("  Verifying replay blocked on reconstructed manager...")
    res_replay = executor2.execute(tc, approval_action_id=action_id)
    if not res_replay.success and "Replay blocked" in res_replay.error:
        print("  [PASS] Replay blocked successfully in Phase 2.")
    else:
        print(f"  [FAIL] Expected replay to be blocked, got: {res_replay.error if not res_replay.success else 'success'}")
        failures += 1

    print("\n-------------------------------------------")
    if failures == 0:
        print("DIAGNOSTIC STATUS: PASS")
    else:
        print(f"DIAGNOSTIC STATUS: FAIL ({failures} failures)")
        sys.exit(1)


if __name__ == "__main__":
    run_diagnostic()
