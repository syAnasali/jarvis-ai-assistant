"""Unit tests for built-in planner tools."""

import pytest
from app.tools.builtin.planner import (
    DecomposeGoalTool,
    ExecutePlanTool,
    GetPlanStatusTool,
    ControlPlanTool,
)
from app.tools.models import ToolResult


def test_decompose_goal_tool_execution():
    tool = DecomposeGoalTool()
    res = tool.execute(objective="Organize my Downloads folder")
    assert isinstance(res, ToolResult)
    assert res.success is True
    assert "plan_id" in res.output


def test_execute_plan_tool_execution():
    tool_decomp = DecomposeGoalTool()
    decomp_res = tool_decomp.execute(objective="Organize Downloads")
    plan_id = decomp_res.output["plan_id"]

    tool_exec = ExecutePlanTool(planner_manager=tool_decomp._manager)
    res = tool_exec.execute(plan_id=plan_id)
    assert isinstance(res, ToolResult)
    assert res.success is True


def test_get_plan_status_tool_execution():
    tool_decomp = DecomposeGoalTool()
    decomp_res = tool_decomp.execute(objective="Organize Downloads")
    plan_id = decomp_res.output["plan_id"]

    tool_status = GetPlanStatusTool(planner_manager=tool_decomp._manager)
    res = tool_status.execute(plan_id=plan_id)
    assert res.success is True
    assert res.output["plan_id"] == plan_id


def test_control_plan_tool_execution():
    tool_decomp = DecomposeGoalTool()
    decomp_res = tool_decomp.execute(objective="Organize Downloads")
    plan_id = decomp_res.output["plan_id"]

    tool_ctrl = ControlPlanTool(planner_manager=tool_decomp._manager)
    res = tool_ctrl.execute(plan_id=plan_id, action="pause")
    assert res.success is True
