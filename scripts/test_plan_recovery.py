"""Diagnostic script testing step failure recovery strategies."""

import sys
sys.path.insert(0, ".")

from app.planner.models import NodeType, PlanNode
from app.planner.recovery import AutonomousRecoveryEngine


def main() -> None:
    print("==================================================")
    print("Testing Plan Failure Recovery Diagnostics")
    print("==================================================")

    engine = AutonomousRecoveryEngine()
    node = PlanNode(
        node_id="test_node_1",
        description="Failing node step",
        node_type=NodeType.TOOL,
        action="list_directory",
        arguments={"path": "InvalidDir"},
        retry_count=0,
        max_retries=2
    )

    action1 = engine.determine_recovery(node, error_text="Directory not found")
    print(f"Recovery Action (retry 0): {action1.action_type} - {action1.reason}")
    assert action1.action_type == "RETRY"
    print("PASS: Retry recovery strategy verified.")

    node_exhausted = PlanNode(
        node_id="test_node_1",
        description="Failing node step",
        node_type=NodeType.TOOL,
        action="list_directory",
        arguments={"path": "InvalidDir"},
        retry_count=2,
        max_retries=2
    )
    action2 = engine.determine_recovery(node_exhausted, error_text="Directory not found")
    print(f"Recovery Action (exhausted): {action2.action_type} - {action2.reason}")
    assert action2.action_type in ("USER_PROMPT", "ALTERNATIVE_TOOL", "ROLLBACK")
    print("PASS: Exhausted retry fallback strategy verified.")

    print("\nALL RECOVERY DIAGNOSTICS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
