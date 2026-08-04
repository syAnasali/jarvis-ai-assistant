"""Unit tests for AutonomousRecoveryEngine."""

import pytest
from app.planner.models import NodeType, PlanNode, RecoveryAction
from app.planner.recovery import AutonomousRecoveryEngine


def test_recovery_engine_retry_strategy():
    engine = AutonomousRecoveryEngine()
    node = PlanNode(
        node_id="n1", description="desc", node_type=NodeType.TOOL, action="a1", retry_count=1, max_retries=3
    )

    action = engine.determine_recovery(node, error_text="Timeout error")
    assert isinstance(action, RecoveryAction)
    assert action.action_type == "RETRY"


def test_recovery_engine_alternative_tool():
    engine = AutonomousRecoveryEngine()
    node = PlanNode(
        node_id="n1",
        description="desc",
        node_type=NodeType.TOOL,
        action="a1",
        retry_count=3,
        max_retries=3,
        metadata={"alternative_tool": "a2"}
    )

    action = engine.determine_recovery(node, error_text="Error")
    assert action.action_type == "ALTERNATIVE_TOOL"
    assert action.alternative_action == "a2"
