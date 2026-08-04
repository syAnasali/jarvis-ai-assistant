"""Unit tests for OutcomeTaskVerifier."""

import pytest
from app.planner.models import NodeType, PlanNode, VerificationResult
from app.planner.verifier import OutcomeTaskVerifier


def test_task_verifier_no_action_passes():
    verifier = OutcomeTaskVerifier()
    node = PlanNode(node_id="n1", description="desc", node_type=NodeType.TOOL, action="a1")

    res = verifier.verify_node(node, execution_output={"ok": True})
    assert isinstance(res, VerificationResult)
    assert res.is_verified is True


def test_task_verifier_inspect_path_rule():
    verifier = OutcomeTaskVerifier()
    node = PlanNode(
        node_id="n1",
        description="desc",
        node_type=NodeType.TOOL,
        action="create_directory",
        arguments={"path": "Downloads/Organized"},
        verification_action="inspect_path"
    )

    res = verifier.verify_node(node, execution_output={"exists": True})
    assert res.is_verified is True
