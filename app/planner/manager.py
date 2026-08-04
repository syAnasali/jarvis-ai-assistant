"""Hierarchical Planner Subsystem Manager acting as orchestrator and coordinator."""

from typing import Any, Dict, List, Optional
from app.core.logger import JarvisLogger
from app.planner.executor import PlanExecutor
from app.planner.graph import TaskGraph
from app.planner.models import Goal, Plan, PlanProgress, PlanStatus
from app.planner.planner import GoalDecomposer
from app.planner.progress import PlanProgressTracker
from app.planner.recovery import AutonomousRecoveryEngine
from app.planner.repository import SQLitePlanRepository
from app.planner.verifier import OutcomeTaskVerifier

logger = JarvisLogger.get_logger("planner_manager")


class PlannerManager:
    """Orchestrates Hierarchical Planning engine components with metrics tracking."""

    def __init__(
        self,
        planner: Optional[GoalDecomposer] = None,
        executor: Optional[PlanExecutor] = None,
        repository: Optional[SQLitePlanRepository] = None,
        progress_tracker: Optional[PlanProgressTracker] = None,
        tool_executor: Optional[Any] = None,
        vision_pipeline: Optional[Any] = None,
        voice_pipeline: Optional[Any] = None,
        memory_manager: Optional[Any] = None
    ) -> None:
        self.planner = planner or GoalDecomposer(memory_manager=memory_manager)
        self.repository = repository or SQLitePlanRepository()
        self.tracker = progress_tracker or PlanProgressTracker()
        self.executor = executor or PlanExecutor(
            tool_executor=tool_executor,
            vision_pipeline=vision_pipeline,
            voice_pipeline=voice_pipeline,
            memory_manager=memory_manager,
            repository=self.repository,
            progress_tracker=self.tracker
        )

        self.metrics: Dict[str, Any] = {
            "goals_decomposed": 0,
            "plans_executed": 0,
            "plans_completed": 0,
            "plans_failed": 0,
            "plans_paused": 0
        }
        self._is_initialized = False

    def initialize(self) -> None:
        """Initializes underlying Planner components."""
        if self._is_initialized:
            return
        logger.info("Initializing PlannerManager components...")
        self._is_initialized = True
        logger.info("PlannerManager initialized successfully.")

    def create_plan_for_goal(self, objective: str) -> Plan:
        """Decomposes an objective string into a persisted Plan."""
        goal = Goal(objective=objective)
        plan = self.planner.decompose_goal(goal)
        self.repository.save_plan(plan)
        self.metrics["goals_decomposed"] += 1
        return plan

    def run_goal(self, objective: str) -> PlanProgress:
        """Creates and executes a plan for an objective string."""
        self.metrics["plans_executed"] += 1
        plan = self.create_plan_for_goal(objective)
        progress = self.executor.execute_plan(plan)
        if progress.completed_nodes == progress.total_nodes:
            self.metrics["plans_completed"] += 1
        else:
            self.metrics["plans_failed"] += 1
        return progress

    def get_plan_status(self, plan_id: str) -> Optional[PlanProgress]:
        """Retrieves current execution progress of a stored plan."""
        plan = self.repository.get_plan(plan_id)
        if not plan:
            return None
        graph = TaskGraph(plan.nodes)
        return self.tracker.calculate_progress(plan, graph)

    def control_plan(self, plan_id: str, action: str) -> Optional[PlanProgress]:
        """Pauses, resumes, or cancels a plan."""
        act = action.lower()
        if act == "pause":
            self.executor.pause_plan(plan_id)
            self.metrics["plans_paused"] += 1
        elif act == "resume":
            return self.executor.resume_plan(plan_id)
        elif act == "cancel":
            self.executor.cancel_plan(plan_id)

        return self.get_plan_status(plan_id)

    def health_check(self) -> Dict[str, Any]:
        """Returns diagnostic parameters and metrics."""
        return {
            "available": self._is_initialized,
            "metrics": self.metrics
        }

    def shutdown(self) -> None:
        """Releases planner resources."""
        self._is_initialized = False
        logger.info("PlannerManager shutdown complete.")
