"""Unit tests for PlanProgressTracker."""

import pytest
from app.planner.graph import TaskGraph
from app.planner.models import Goal, NodeStatus, NodeType, Plan, PlanNode, PlanProgress
from app.planner.progress import PlanProgressTracker


def test_plan_progress_calculation():
    tracker = PlanProgressTracker(bar_length=10)
    n1 = PlanNode(node_id="n1", description="desc1", node_type=NodeType.TOOL, action="a1", status=NodeStatus.COMPLETED)
    n2 = PlanNode(node_id="n2", description="desc2", node_type=NodeType.TOOL, action="a2", status=NodeStatus.PENDING)
    nodes = {"n1": n1, "n2": n2}
    graph = TaskGraph(nodes)
    goal = Goal(objective="Progress goal")
    plan = Plan(plan_id="p_prog_1", goal=goal, nodes=nodes)

    progress = tracker.calculate_progress(plan, graph)
    assert isinstance(progress, PlanProgress)
    assert progress.completed_nodes == 1
    assert progress.percentage == 50.0
    assert progress.progress_bar == "[█████░░░░░]"
