"""Abstract interface contracts for the Hierarchical Planning Engine."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from app.planner.models import (
    Goal,
    Plan,
    PlanNode,
    PlanProgress,
    RecoveryAction,
    VerificationResult,
    ExecutionStep,
)


class HierarchicalPlanner(ABC):
    """Abstract interface for goal decomposition into DAG task graphs."""

    @abstractmethod
    def decompose_goal(self, goal: Goal) -> Plan:
        """Decomposes a user goal objective into a DAG task plan."""
        pass


class TaskGraphExecutor(ABC):
    """Abstract interface for executing and managing DAG task plans."""

    @abstractmethod
    def execute_plan(self, plan: Plan) -> PlanProgress:
        """Executes a DAG task plan."""
        pass

    @abstractmethod
    def pause_plan(self, plan_id: str) -> None:
        """Pauses a running plan."""
        pass

    @abstractmethod
    def resume_plan(self, plan_id: str) -> PlanProgress:
        """Resumes a paused plan."""
        pass

    @abstractmethod
    def cancel_plan(self, plan_id: str) -> None:
        """Cancels execution of a plan."""
        pass


class TaskVerifier(ABC):
    """Abstract interface for verifying step execution outcomes."""

    @abstractmethod
    def verify_node(self, node: PlanNode, execution_output: Any) -> VerificationResult:
        """Verifies whether a completed node achieved its intended outcome."""
        pass


class RecoveryEngine(ABC):
    """Abstract interface for handling step failures and recovery strategies."""

    @abstractmethod
    def determine_recovery(
        self,
        node: PlanNode,
        error_text: str,
        verification: Optional[VerificationResult] = None
    ) -> RecoveryAction:
        """Determines the recovery action (retry, alternative tool, rollback, user prompt)."""
        pass


class PlanRepository(ABC):
    """Abstract interface for SQLite persistence of plans and execution state."""

    @abstractmethod
    def save_plan(self, plan: Plan) -> None:
        """Persists or updates a plan and its DAG nodes."""
        pass

    @abstractmethod
    def get_plan(self, plan_id: str) -> Optional[Plan]:
        """Retrieves a plan by plan_id."""
        pass

    @abstractmethod
    def list_plans(self) -> List[Plan]:
        """Lists all stored plans."""
        pass

    @abstractmethod
    def log_execution(self, step: ExecutionStep) -> None:
        """Logs an execution step record."""
        pass
