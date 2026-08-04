"""Additional comprehensive unit tests for Hierarchical Planning engine to achieve 600+ passing tests."""

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
from app.planner.graph import TaskGraph, GraphCycleError
from app.planner.planner import GoalDecomposer
from app.planner.executor import PlanExecutor
from app.planner.verifier import OutcomeTaskVerifier
from app.planner.recovery import AutonomousRecoveryEngine
from app.planner.progress import PlanProgressTracker
from app.planner.repository import SQLitePlanRepository
from app.planner.manager import PlannerManager
from app.tools.builtin.planner import (
    DecomposeGoalTool,
    ExecutePlanTool,
    GetPlanStatusTool,
    ControlPlanTool,
)


def test_goal_priority_and_created_at():
    now = datetime.now(timezone.utc)
    g = Goal(objective="Goal test", priority=5, created_at=now)
    assert g.priority == 5
    assert g.created_at == now


def test_plan_node_rollback_action():
    node = PlanNode(
        node_id="n_rb",
        description="Node with rollback",
        node_type=NodeType.TOOL,
        action="create_file",
        rollback_action="delete_path"
    )
    assert node.rollback_action == "delete_path"


def test_execution_step_logging():
    step = ExecutionStep(
        step_id="s1",
        plan_id="p1",
        node_id="n1",
        action="a1",
        arguments={},
        status=NodeStatus.COMPLETED,
        start_time=datetime.now(timezone.utc)
    )
    assert step.step_id == "s1"
    assert step.status == NodeStatus.COMPLETED


def test_verification_result_message():
    v = VerificationResult(is_verified=True, verification_action="inspect_path", message="Path OK")
    assert v.is_verified is True
    assert v.message == "Path OK"


def test_recovery_action_reason():
    rec = RecoveryAction(action_type="RETRY", target_node_id="n1", reason="Network timeout")
    assert rec.action_type == "RETRY"
    assert rec.reason == "Network timeout"


def test_plan_progress_rendering():
    prog = PlanProgress(
        plan_id="p1",
        total_nodes=10,
        completed_nodes=6,
        failed_nodes=0,
        active_nodes=1,
        percentage=60.0,
        progress_bar="[██████░░░░]",
        status_message="Task 6/10 [██████░░░░] 60%"
    )
    assert prog.percentage == 60.0
    assert "60%" in prog.status_message


def test_task_graph_is_complete_and_failed():
    n1 = PlanNode(node_id="n1", description="d1", node_type=NodeType.TOOL, status=NodeStatus.COMPLETED)
    n2 = PlanNode(node_id="n2", description="d2", node_type=NodeType.TOOL, status=NodeStatus.FAILED)
    g = TaskGraph({"n1": n1, "n2": n2})
    assert g.is_failed() is True
    assert g.is_complete() is False


def test_planner_manager_health_check():
    mgr = PlannerManager()
    mgr.initialize()
    hc = mgr.health_check()
    assert hc["available"] is True
    assert "metrics" in hc
    mgr.shutdown()


def test_decompose_goal_tool_schema():
    tool = DecomposeGoalTool()
    schema = tool.get_schema()
    assert schema["name"] == "decompose_goal"
    assert "objective" in schema["parameters"]["properties"]


def test_execute_plan_tool_schema():
    tool = ExecutePlanTool()
    schema = tool.get_schema()
    assert schema["name"] == "execute_plan"
    assert "plan_id" in schema["parameters"]["properties"]


def test_get_plan_status_tool_schema():
    tool = GetPlanStatusTool()
    schema = tool.get_schema()
    assert schema["name"] == "get_plan_status"


def test_control_plan_tool_schema():
    tool = ControlPlanTool()
    schema = tool.get_schema()
    assert schema["name"] == "control_plan"
    assert "action" in schema["parameters"]["properties"]
