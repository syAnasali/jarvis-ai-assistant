"""Unit tests for Planner Voice integration."""

import pytest
from unittest.mock import MagicMock
from app.planner.executor import PlanExecutor
from app.planner.planner import GoalDecomposer
from app.planner.models import Goal


def test_planner_speaks_plan_explanation_on_start():
    voice_mock = MagicMock()
    decomposer = GoalDecomposer()
    goal = Goal(objective="Organize Downloads")
    plan = decomposer.decompose_goal(goal)

    executor = PlanExecutor(voice_pipeline=voice_mock)
    executor.execute_plan(plan)

    assert voice_mock.speak.called
