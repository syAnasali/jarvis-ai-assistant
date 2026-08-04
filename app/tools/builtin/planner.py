"""Built-in Planner tools for goal decomposition, plan execution, status retrieval, and plan control."""

from typing import Any, Dict, Optional
from app.planner.manager import PlannerManager
from app.tools.base import BaseTool
from app.tools.models import ToolPermission, ToolResult


class DecomposeGoalTool(BaseTool):
    """Tool to decompose a high-level goal objective into an executable DAG task plan."""

    name = "decompose_goal"
    description = "Decomposes a complex objective into an ordered DAG task plan with verification steps."
    permission_level = ToolPermission.SAFE

    parameters = {
        "type": "object",
        "properties": {
            "objective": {
                "type": "string",
                "description": "High-level goal objective (e.g. 'Organize my Downloads folder')."
            }
        },
        "required": ["objective"]
    }

    def __init__(self, planner_manager: Optional[PlannerManager] = None) -> None:
        self._manager = planner_manager or PlannerManager()

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "permission_level": self.permission_level.value,
            "parameters": self.parameters
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        objective = kwargs.get("objective", "")
        if not objective:
            return ToolResult(tool_name=self.name, success=False, output={}, error="Objective must not be empty.")

        try:
            plan = self._manager.create_plan_for_goal(objective)
            node_descriptions = [f"{n.node_id}: {n.description}" for n in plan.nodes.values()]

            return ToolResult(
                tool_name=self.name,
                success=True,
                output={
                    "plan_id": plan.plan_id,
                    "goal": plan.goal.objective,
                    "total_nodes": len(plan.nodes),
                    "node_sequence": node_descriptions,
                    "status": plan.status.value
                }
            )
        except Exception as e:
            return ToolResult(tool_name=self.name, success=False, output={}, error=f"Decompose goal failed: {e}")


class ExecutePlanTool(BaseTool):
    """Tool to execute a DAG task plan."""

    name = "execute_plan"
    description = "Executes an existing DAG task plan by plan_id, running and verifying nodes."
    permission_level = ToolPermission.SAFE

    parameters = {
        "type": "object",
        "properties": {
            "plan_id": {
                "type": "string",
                "description": "Unique plan_id identifier to execute."
            }
        },
        "required": ["plan_id"]
    }

    def __init__(self, planner_manager: Optional[PlannerManager] = None) -> None:
        self._manager = planner_manager or PlannerManager()

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "permission_level": self.permission_level.value,
            "parameters": self.parameters
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        plan_id = kwargs.get("plan_id", "")
        if not plan_id:
            return ToolResult(tool_name=self.name, success=False, output={}, error="plan_id must not be empty.")

        try:
            plan = self._manager.repository.get_plan(plan_id)
            if not plan:
                return ToolResult(tool_name=self.name, success=False, output={}, error=f"Plan '{plan_id}' not found.")

            progress = self._manager.executor.execute_plan(plan)
            return ToolResult(
                tool_name=self.name,
                success=True,
                output={
                    "plan_id": progress.plan_id,
                    "percentage": progress.percentage,
                    "progress_bar": progress.progress_bar,
                    "completed_nodes": progress.completed_nodes,
                    "total_nodes": progress.total_nodes,
                    "status_message": progress.status_message
                }
            )
        except Exception as e:
            return ToolResult(tool_name=self.name, success=False, output={}, error=f"Execute plan failed: {e}")


class GetPlanStatusTool(BaseTool):
    """Tool to retrieve live execution progress and task graph status for a plan."""

    name = "get_plan_status"
    description = "Retrieves live completion percentage, progress bar, and node status for a plan."
    permission_level = ToolPermission.SAFE

    parameters = {
        "type": "object",
        "properties": {
            "plan_id": {
                "type": "string",
                "description": "Unique plan_id identifier."
            }
        },
        "required": ["plan_id"]
    }

    def __init__(self, planner_manager: Optional[PlannerManager] = None) -> None:
        self._manager = planner_manager or PlannerManager()

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "permission_level": self.permission_level.value,
            "parameters": self.parameters
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        plan_id = kwargs.get("plan_id", "")
        if not plan_id:
            return ToolResult(tool_name=self.name, success=False, output={}, error="plan_id must not be empty.")

        try:
            progress = self._manager.get_plan_status(plan_id)
            if not progress:
                return ToolResult(tool_name=self.name, success=False, output={}, error=f"Plan '{plan_id}' not found.")

            return ToolResult(
                tool_name=self.name,
                success=True,
                output={
                    "plan_id": progress.plan_id,
                    "percentage": progress.percentage,
                    "progress_bar": progress.progress_bar,
                    "completed_nodes": progress.completed_nodes,
                    "total_nodes": progress.total_nodes,
                    "status_message": progress.status_message
                }
            )
        except Exception as e:
            return ToolResult(tool_name=self.name, success=False, output={}, error=f"Get plan status failed: {e}")


class ControlPlanTool(BaseTool):
    """Tool to pause, resume, or cancel execution of a task plan."""

    name = "control_plan"
    description = "Controls plan execution lifecycle (action: 'pause', 'resume', 'cancel')."
    permission_level = ToolPermission.SAFE

    parameters = {
        "type": "object",
        "properties": {
            "plan_id": {
                "type": "string",
                "description": "Unique plan_id identifier."
            },
            "action": {
                "type": "string",
                "enum": ["pause", "resume", "cancel"],
                "description": "Control action ('pause', 'resume', 'cancel')."
            }
        },
        "required": ["plan_id", "action"]
    }

    def __init__(self, planner_manager: Optional[PlannerManager] = None) -> None:
        self._manager = planner_manager or PlannerManager()

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "permission_level": self.permission_level.value,
            "parameters": self.parameters
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        plan_id = kwargs.get("plan_id", "")
        action = kwargs.get("action", "")

        try:
            progress = self._manager.control_plan(plan_id, action)
            return ToolResult(
                tool_name=self.name,
                success=True,
                output={
                    "plan_id": plan_id,
                    "action_executed": action,
                    "status_message": progress.status_message if progress else f"Action '{action}' issued."
                }
            )
        except Exception as e:
            return ToolResult(tool_name=self.name, success=False, output={}, error=f"Control plan failed: {e}")
