"""Unit tests verifying Vision node delegation in Hierarchical PlanExecutor."""

import pytest
from unittest.mock import MagicMock
from app.planner.executor import PlanExecutor
from app.planner.models import Goal, NodeType, Plan, PlanNode


def test_plan_executor_delegates_vision_node():
    vision_mock = MagicMock()
    vision_mock.process_fullscreen.return_value = "Visual description"

    node = PlanNode(
        node_id="n_vis",
        description="Observe desktop",
        node_type=NodeType.VISION,
        action="capture_screen",
        arguments={"prompt": "Observe desktop layout"}
    )
    goal = Goal(objective="Observe desktop workspace")
    plan = Plan(plan_id="p_vis_test", goal=goal, nodes={"n_vis": node})

    executor = PlanExecutor(vision_pipeline=vision_mock)
    progress = executor.execute_plan(plan)

    assert progress.completed_nodes == 1
    assert vision_mock.process_fullscreen.called
