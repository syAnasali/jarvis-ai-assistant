"""Unit tests for Hierarchical Planning domain models."""

import pytest
from datetime import datetime, timezone
from app.planner.models import (
    Goal,
    Plan,
    PlanNode,
    ExecutionStep,
    VerificationResult,
    RecoveryAction,
    PlanStatus,
    NodeStatus,
    NodeType,
    PlanProgress,
)


def test_goal_validation():
    g = Goal(objective="Organize Downloads", priority=1)
    assert g.objective == "Organize Downloads"
    assert g.goal_id.startswith("goal_")

    with pytest.raises(ValueError):
        Goal(objective="")


def test_plan_node_validation():
    node = PlanNode(
        node_id="n1",
        description="Inspect directory",
        node_type=NodeType.TOOL,
        action="list_directory",
        arguments={"path": "Downloads"}
    )
    assert node.node_id == "n1"
    assert node.status == NodeStatus.PENDING
    assert node.arguments["path"] == "Downloads"

    with pytest.raises(ValueError):
        PlanNode(node_id="", description="desc", node_type=NodeType.TOOL)


def test_plan_dag_node_container():
    goal = Goal(objective="Test goal")
    node = PlanNode(node_id="n1", description="desc", node_type=NodeType.TOOL, action="act")
    plan = Plan(plan_id="p1", goal=goal, nodes={"n1": node})

    assert plan.plan_id == "p1"
    assert plan.status == PlanStatus.CREATED
    assert "n1" in plan.nodes
