"""Unit tests for PlanExecutor."""

import pytest
from app.planner.executor import PlanExecutor
from app.planner.planner import GoalDecomposer
from app.planner.models import Goal, PlanStatus


def test_plan_executor_runs_plan_to_completion():
    decomposer = GoalDecomposer()
    goal = Goal(objective="Organize Downloads")
    plan = decomposer.decompose_goal(goal)

    executor = PlanExecutor()
    progress = executor.execute_plan(plan)

    assert progress.completed_nodes == progress.total_nodes
    assert progress.percentage == 100.0
