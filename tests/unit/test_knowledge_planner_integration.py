"""Unit tests for Knowledge RAG integration with Planner."""

import pytest
from app.planner.planner import GoalDecomposer
from app.planner.models import Goal


def test_planner_decomposes_goal_with_document_understanding():
    decomposer = GoalDecomposer()
    goal = Goal(objective="Read PDF notes and summarize AI research")

    plan = decomposer.decompose_goal(goal)
    assert len(plan.nodes) >= 2
