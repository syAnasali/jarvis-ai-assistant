"""Plan Executor delegating step execution to ToolExecutor, Vision, Voice, and Memory runtimes."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from app.core.exceptions import JarvisError
from app.core.logger import JarvisLogger
from app.planner.graph import TaskGraph
from app.planner.interfaces import PlanRepository, RecoveryEngine, TaskGraphExecutor, TaskVerifier
from app.planner.models import (
    ExecutionStep,
    NodeStatus,
    NodeType,
    Plan,
    PlanNode,
    PlanProgress,
    PlanStatus,
)
from app.planner.progress import PlanProgressTracker
from app.planner.recovery import AutonomousRecoveryEngine
from app.planner.repository import SQLitePlanRepository
from app.planner.verifier import OutcomeTaskVerifier
from app.utils.id_generator import generate_step_id

logger = JarvisLogger.get_logger("plan_executor")


class PlanExecutor(TaskGraphExecutor):
    """Executes DAG task plans by delegating tasks to system runtimes."""

    def __init__(
        self,
        tool_executor: Optional[Any] = None,
        vision_pipeline: Optional[Any] = None,
        voice_pipeline: Optional[Any] = None,
        memory_manager: Optional[Any] = None,
        approval_manager: Optional[Any] = None,
        verifier: Optional[TaskVerifier] = None,
        recovery_engine: Optional[RecoveryEngine] = None,
        repository: Optional[PlanRepository] = None,
        progress_tracker: Optional[PlanProgressTracker] = None
    ) -> None:
        self.tool_executor = tool_executor
        self.vision_pipeline = vision_pipeline
        self.voice_pipeline = voice_pipeline
        self.memory_manager = memory_manager
        self.approval_manager = approval_manager

        self.verifier = verifier or OutcomeTaskVerifier(tool_executor=self.tool_executor)
        self.recovery_engine = recovery_engine or AutonomousRecoveryEngine()
        self.repository = repository or SQLitePlanRepository()
        self.tracker = progress_tracker or PlanProgressTracker()

        self._active_plans: Dict[str, PlanStatus] = {}

    def execute_plan(self, plan: Plan) -> PlanProgress:
        """Executes a DAG task plan."""
        logger.info(f"Commencing execution of plan '{plan.plan_id}' (goal='{plan.goal.objective}')...")
        graph = TaskGraph(plan.nodes)
        self._active_plans[plan.plan_id] = PlanStatus.RUNNING

        # Initial progress notification & SQLite save
        current_plan = self._update_plan_status(plan, graph, PlanStatus.RUNNING)
        self.repository.save_plan(current_plan)

        # Voice explanation if voice pipeline is active
        if self.voice_pipeline:
            try:
                self.voice_pipeline.speak(f"Starting plan: {plan.goal.objective}")
            except Exception:
                pass

        # Execution loop traversing topological DAG ready nodes
        while self._active_plans.get(plan.plan_id) == PlanStatus.RUNNING and not graph.is_complete():
            ready_nodes = graph.get_ready_nodes()
            if not ready_nodes:
                if graph.is_failed():
                    logger.warning(f"Plan '{plan.plan_id}' execution stalled due to unrecoverable node failures.")
                    current_plan = self._update_plan_status(current_plan, graph, PlanStatus.FAILED)
                    break
                break

            for node in ready_nodes:
                if self._active_plans.get(plan.plan_id) != PlanStatus.RUNNING:
                    break

                self._execute_single_node(current_plan, graph, node)

        # Final status evaluation
        if graph.is_complete() and not graph.is_failed():
            current_plan = self._update_plan_status(current_plan, graph, PlanStatus.COMPLETED)
            if self.voice_pipeline:
                try:
                    self.voice_pipeline.speak(f"Plan completed successfully: {plan.goal.objective}")
                except Exception:
                    pass
        elif self._active_plans.get(plan.plan_id) == PlanStatus.PAUSED:
            current_plan = self._update_plan_status(current_plan, graph, PlanStatus.PAUSED)
        elif self._active_plans.get(plan.plan_id) == PlanStatus.CANCELLED:
            current_plan = self._update_plan_status(current_plan, graph, PlanStatus.CANCELLED)

        self.repository.save_plan(current_plan)
        return self.tracker.calculate_progress(current_plan, graph)

    def _execute_single_node(self, plan: Plan, graph: TaskGraph, node: PlanNode) -> None:
        """Executes an individual PlanNode and verifies outcome."""
        logger.info(f"Executing node '{node.node_id}' ({node.node_type.value}: '{node.action}')...")
        start_time = datetime.now(timezone.utc)

        running_node = PlanNode(
            node_id=node.node_id,
            description=node.description,
            node_type=node.node_type,
            action=node.action,
            arguments=dict(node.arguments),
            dependencies=list(node.dependencies),
            status=NodeStatus.RUNNING,
            retry_count=node.retry_count,
            max_retries=node.max_retries,
            verification_action=node.verification_action,
            rollback_action=node.rollback_action,
            metadata=dict(node.metadata)
        )
        graph.update_node(running_node)
        self.tracker.calculate_progress(plan, graph)

        output: Any = None
        error_text: Optional[str] = None

        try:
            # Delegate based on NodeType
            if node.node_type == NodeType.VISION and self.vision_pipeline:
                output = self.vision_pipeline.process_fullscreen(
                    prompt=node.arguments.get("prompt", "Analyze visual content.")
                )
            elif node.node_type == NodeType.TOOL and self.tool_executor:
                res = self.tool_executor.execute_tool(node.action, dict(node.arguments))
                output = getattr(res, "output", res)
            else:
                output = {"status": "executed", "action": node.action}

            # Verification Step
            v_result = self.verifier.verify_node(running_node, output)
            if v_result.is_verified:
                completed_node = PlanNode(
                    node_id=node.node_id,
                    description=node.description,
                    node_type=node.node_type,
                    action=node.action,
                    arguments=dict(node.arguments),
                    dependencies=list(node.dependencies),
                    status=NodeStatus.COMPLETED,
                    result=output,
                    retry_count=node.retry_count,
                    max_retries=node.max_retries,
                    verification_action=node.verification_action,
                    rollback_action=node.rollback_action,
                    metadata=dict(node.metadata)
                )
                graph.update_node(completed_node)
            else:
                error_text = v_result.message
                self._handle_node_failure(plan, graph, running_node, error_text, v_result)

        except Exception as e:
            error_text = str(e)
            logger.error(f"Error executing node '{node.node_id}': {e}")
            self._handle_node_failure(plan, graph, running_node, error_text, None)

        end_time = datetime.now(timezone.utc)
        step = ExecutionStep(
            step_id=generate_step_id(),
            plan_id=plan.plan_id,
            node_id=node.node_id,
            action=node.action,
            arguments=dict(node.arguments),
            status=graph.nodes[node.node_id].status,
            start_time=start_time,
            end_time=end_time,
            output=output,
            error_text=error_text
        )
        self.repository.log_execution(step)

    def _handle_node_failure(
        self,
        plan: Plan,
        graph: TaskGraph,
        node: PlanNode,
        error_text: str,
        verification: Optional[Any]
    ) -> None:
        """Applies recovery strategy when a node fails or verification checks fail."""
        recovery = self.recovery_engine.determine_recovery(node, error_text, verification)

        if recovery.action_type == "RETRY":
            retry_node = PlanNode(
                node_id=node.node_id,
                description=node.description,
                node_type=node.node_type,
                action=node.action,
                arguments=dict(node.arguments),
                dependencies=list(node.dependencies),
                status=NodeStatus.PENDING,
                retry_count=node.retry_count + 1,
                max_retries=node.max_retries,
                verification_action=node.verification_action,
                rollback_action=node.rollback_action,
                metadata=dict(node.metadata)
            )
            graph.update_node(retry_node)
        elif recovery.action_type == "ALTERNATIVE_TOOL" and recovery.alternative_action:
            alt_node = PlanNode(
                node_id=node.node_id,
                description=node.description,
                node_type=node.node_type,
                action=recovery.alternative_action,
                arguments=dict(recovery.alternative_arguments),
                dependencies=list(node.dependencies),
                status=NodeStatus.PENDING,
                retry_count=0,
                max_retries=node.max_retries,
                verification_action=node.verification_action,
                rollback_action=node.rollback_action,
                metadata=dict(node.metadata)
            )
            graph.update_node(alt_node)
        else:
            failed_node = PlanNode(
                node_id=node.node_id,
                description=node.description,
                node_type=node.node_type,
                action=node.action,
                arguments=dict(node.arguments),
                dependencies=list(node.dependencies),
                status=NodeStatus.FAILED,
                retry_count=node.retry_count,
                max_retries=node.max_retries,
                verification_action=node.verification_action,
                rollback_action=node.rollback_action,
                metadata=dict(node.metadata)
            )
            graph.update_node(failed_node)

    def pause_plan(self, plan_id: str) -> None:
        """Pauses a running plan."""
        logger.info(f"Pausing execution for plan '{plan_id}'...")
        self._active_plans[plan_id] = PlanStatus.PAUSED

    def resume_plan(self, plan_id: str) -> PlanProgress:
        """Resumes a paused plan."""
        logger.info(f"Resuming execution for plan '{plan_id}'...")
        plan = self.repository.get_plan(plan_id)
        if not plan:
            raise JarvisError(f"Cannot resume unknown plan: '{plan_id}'.")
        return self.execute_plan(plan)

    def cancel_plan(self, plan_id: str) -> None:
        """Cancels a running plan."""
        logger.info(f"Cancelling execution for plan '{plan_id}'...")
        self._active_plans[plan_id] = PlanStatus.CANCELLED

    def _update_plan_status(self, plan: Plan, graph: TaskGraph, status: PlanStatus) -> Plan:
        """Helper to create updated Plan instance."""
        return Plan(
            plan_id=plan.plan_id,
            goal=plan.goal,
            nodes=dict(graph.nodes),
            status=status,
            created_at=plan.created_at,
            updated_at=datetime.now(timezone.utc),
            metadata=dict(plan.metadata)
        )
