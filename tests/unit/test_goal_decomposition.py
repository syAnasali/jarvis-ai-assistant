"""Unit tests for GoalDecomposer."""

import pytest
from app.planner.planner import GoalDecomposer
from app.planner.models import Goal, Plan, PlanStatus


def test_goal_decomposition_downloads_pattern():
    decomposer = GoalDecomposer()
    goal = Goal(objective="Organize my Downloads folder")

    plan = decomposer.decompose_goal(goal)
    assert isinstance(plan, Plan)
    assert plan.status == PlanStatus.CREATED
    assert len(plan.nodes) == 2
    assert "node_inspect_downloads" in plan.nodes


def test_goal_decomposition_workspace_pattern():
    decomposer = GoalDecomposer()
    goal = Goal(objective="Prepare my development workspace")

    plan = decomposer.decompose_goal(goal)
    assert len(plan.nodes) == 2
    assert "node_observe_desktop" in plan.nodes
