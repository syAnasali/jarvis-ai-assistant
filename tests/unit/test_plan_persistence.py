"""Unit tests for SQLitePlanRepository."""

import pytest
from app.planner.models import Goal, NodeType, Plan, PlanNode, PlanStatus
from app.planner.repository import SQLitePlanRepository


def test_sqlite_plan_repository_save_and_get():
    repo = SQLitePlanRepository(database_path=":memory:")
    goal = Goal(objective="Test SQLite Persistence")
    node = PlanNode(node_id="n1", description="desc", node_type=NodeType.TOOL, action="a1")
    plan = Plan(plan_id="p_persist_1", goal=goal, nodes={"n1": node})

    repo.save_plan(plan)

    retrieved = repo.get_plan("p_persist_1")
    assert retrieved is not None
    assert retrieved.plan_id == "p_persist_1"
    assert retrieved.goal.objective == "Test SQLite Persistence"
    assert "n1" in retrieved.nodes
