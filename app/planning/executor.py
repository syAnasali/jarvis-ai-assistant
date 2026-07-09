"""Task planning execution engine."""

import time
from datetime import datetime, timezone
from typing import Any, Dict, List
from app.config.settings import settings
from app.core.exceptions import PlanLimitError, PlanExecutionError, StepExecutionError
from app.core.logger import JarvisLogger
from app.ai.manager import LLMManager
from app.ai.scheduler import InferencePriority
from app.ai.models import GenerationProfile
from app.agent.models import ToolCall
from app.tools.executor import ToolExecutor
from app.tools.registry import ToolRegistry
from app.planning.models import TaskPlan, PlanStatus, StepStatus, StepType, StepObservation, PlanExecutionResult
from app.planning.validator import PlanValidator
from app.planning.metrics import PlanningMetrics
from app.planning.prompts import REASONING_PROMPT, SYNTHESIS_PROMPT, FAILURE_SYNTHESIS_PROMPT

logger = JarvisLogger.get_logger("task_executor")


class TaskExecutor:
    """Coordinates sequentially executing steps, collecting observations, and synthesizing final answers."""

    def __init__(
        self,
        llm_manager: LLMManager,
        registry: ToolRegistry,
        tool_executor: ToolExecutor,
        validator: PlanValidator | None = None
    ) -> None:
        """Initializes the TaskExecutor.

        Args:
            llm_manager: Manager to route inference calls.
            registry: The tool registry.
            tool_executor: The safe tool executor boundary.
            validator: Optional validator override.
        """
        self._llm_manager = llm_manager
        self._registry = registry
        self._tool_executor = tool_executor
        self._validator = validator or PlanValidator(registry)

    def execute(self, plan: TaskPlan, original_request_text: str, routing_confidence: float = 1.0) -> PlanExecutionResult:
        """Runs the validation and sequential execution lifecycle for a TaskPlan.

        Args:
            plan: The TaskPlan to execute.
            original_request_text: The user's original raw prompt text.
            routing_confidence: The confidence score from the router.

        Returns:
            PlanExecutionResult: The aggregated result of plan execution.

        Raises:
            PlanLimitError: If plan length constraints are violated.
            PlanExecutionError: For unexpected programming or system failures.
        """
        start_time = time.perf_counter()
        
        # 1. Defense-in-depth steps limit check
        max_steps = settings.planning_max_steps
        if len(plan.steps) > max_steps:
            logger.error(f"Plan validation bypassed, step count {len(plan.steps)} exceeds limit {max_steps}.")
            raise PlanLimitError(f"Plan exceeds the maximum limit of {max_steps} steps.")

        # 2. Structural plan validation
        try:
            self._validator.validate(plan)
            plan.status = PlanStatus.VALIDATED
        except Exception as e:
            logger.error(f"Plan validation failed: {e}")
            raise

        plan.status = PlanStatus.RUNNING
        logger.info(f"Starting plan execution: plan_id={plan.plan_id}, steps={len(plan.steps)}")

        observations: List[StepObservation] = []
        steps_completed = 0
        steps_failed = 0
        steps_skipped = 0
        tool_calls_count = 0
        reasoning_calls_count = 0
        synthesis_calls_count = 0

        # Sort steps by sequence number to ensure chronological ordering
        ordered_steps = sorted(plan.steps, key=lambda s: s.sequence)
        failed_step_ref = None
        failure_reason = ""

        for step in ordered_steps:
            if failed_step_ref is not None:
                # Subsequent steps are marked SKIPPED after a failure
                step.status = StepStatus.SKIPPED
                steps_skipped += 1
                continue

            step.status = StepStatus.RUNNING
            step_start = time.perf_counter()
            logger.info(f"Running step {step.sequence}: {step.description}")

            try:
                if step.step_type == StepType.TOOL:
                    # TOOL step execution
                    tc = ToolCall(tool_name=step.tool_name, arguments=step.tool_arguments)
                    tool_calls_count += 1
                    
                    tool_result = self._tool_executor.execute(tc)
                    
                    obs_content = ""
                    success = tool_result.success
                    if success:
                        step.status = StepStatus.COMPLETED
                        steps_completed += 1
                        obs_content = str(tool_result.output) if tool_result.output is not None else ""
                    else:
                        step.status = StepStatus.FAILED
                        steps_failed += 1
                        obs_content = tool_result.error or "Unknown tool execution failure."
                        failed_step_ref = step
                        failure_reason = obs_content

                    obs = StepObservation(
                        step_id=step.step_id,
                        step_sequence=step.sequence,
                        step_type=step.step_type,
                        success=success,
                        content=obs_content,
                        tool_name=step.tool_name,
                        created_at=datetime.now(timezone.utc)
                    )
                    observations.append(obs)

                elif step.step_type == StepType.REASONING:
                    # REASONING step execution using LLMManager
                    reasoning_calls_count += 1
                    
                    # Prepare bounded observation context
                    bounded_obs = self._get_bounded_observations(observations)
                    
                    prompt = REASONING_PROMPT.format(
                        goal=plan.goal,
                        step_description=step.description,
                        observations="\n\n".join(
                            f"Step {o.step_sequence} ({o.step_type.name}): {o.content}"
                            for o in bounded_obs
                        )
                    )
                    messages = [{"role": "user", "content": prompt}]
                    
                    gen_result = self._llm_manager.generate(
                        messages,
                        profile=GenerationProfile.BALANCED,
                        priority=InferencePriority.FOREGROUND
                    )
                    
                    conclusion = self._extract_text(gen_result)
                    step.status = StepStatus.COMPLETED
                    steps_completed += 1
                    
                    obs = StepObservation(
                        step_id=step.step_id,
                        step_sequence=step.sequence,
                        step_type=step.step_type,
                        success=True,
                        content=conclusion,
                        created_at=datetime.now(timezone.utc)
                    )
                    observations.append(obs)

                elif step.step_type == StepType.SYNTHESIS:
                    # SYNTHESIS step execution using LLMManager
                    synthesis_calls_count += 1
                    
                    bounded_obs = self._get_bounded_observations(observations)
                    summary_lines = []
                    for o in bounded_obs:
                        status_str = "Success" if o.success else "Failed"
                        summary_lines.append(
                            f"Step {o.step_sequence}: {o.step_type.name} - {o.tool_name or 'N/A'} - {status_str}\nObservation: {o.content}"
                        )
                    
                    prompt = SYNTHESIS_PROMPT.format(
                        request=original_request_text,
                        goal=plan.goal,
                        observations_summary="\n\n".join(summary_lines)
                    )
                    messages = [{"role": "user", "content": prompt}]
                    
                    gen_result = self._llm_manager.generate(
                        messages,
                        profile=GenerationProfile.BALANCED,
                        priority=InferencePriority.FOREGROUND
                    )
                    
                    final_response = self._extract_text(gen_result)
                    step.status = StepStatus.COMPLETED
                    steps_completed += 1
                    
                    obs = StepObservation(
                        step_id=step.step_id,
                        step_sequence=step.sequence,
                        step_type=step.step_type,
                        success=True,
                        content=final_response,
                        created_at=datetime.now(timezone.utc)
                    )
                    observations.append(obs)

            except Exception as e:
                # Handle unexpected execution errors for a specific step
                logger.error(f"Error executing step {step.sequence}: {e}")
                step.status = StepStatus.FAILED
                steps_failed += 1
                failed_step_ref = step
                failure_reason = str(e)
                
                obs = StepObservation(
                    step_id=step.step_id,
                    step_sequence=step.sequence,
                    step_type=step.step_type,
                    success=False,
                    content=f"Unexpected step execution exception: {failure_reason}",
                    tool_name=step.tool_name,
                    created_at=datetime.now(timezone.utc)
                )
                observations.append(obs)

        # 3. Finalize plan outcome
        duration_ms = (time.perf_counter() - start_time) * 1000
        
        if failed_step_ref is not None:
            plan.status = PlanStatus.FAILED
            logger.warning(f"Plan failed at step {failed_step_ref.sequence}.")
            
            # Formulate failure synthesis response
            final_text = self._synthesize_failure(
                original_request_text=original_request_text,
                failed_step=failed_step_ref,
                reason=failure_reason,
                observations=observations
            )
            success_status = False
        else:
            plan.status = PlanStatus.COMPLETED
            # Retrieve the last observation content (the output of the final SYNTHESIS step)
            final_text = observations[-1].content
            success_status = True

        metrics = PlanningMetrics(
            execution_mode="planned",
            routing_confidence=routing_confidence,
            planning_duration_ms=0.0,  # formulated prior to execution
            plan_steps_total=len(plan.steps),
            tool_steps=sum(1 for s in plan.steps if s.step_type == StepType.TOOL),
            reasoning_steps=sum(1 for s in plan.steps if s.step_type == StepType.REASONING),
            synthesis_steps=sum(1 for s in plan.steps if s.step_type == StepType.SYNTHESIS),
            steps_completed=steps_completed,
            steps_failed=steps_failed,
            steps_skipped=steps_skipped,
            tool_calls=tool_calls_count,
            reasoning_model_calls=reasoning_calls_count,
            synthesis_model_calls=synthesis_calls_count,
            total_execution_duration_ms=duration_ms,
            metadata={}
        )

        logger.info(
            f"Planned execution completed: "
            f"plan_id={plan.plan_id}, "
            f"steps={len(plan.steps)}, "
            f"completed={steps_completed}, "
            f"failed={steps_failed}, "
            f"tool_calls={tool_calls_count}, "
            f"model_calls={reasoning_calls_count + synthesis_calls_count}, "
            f"duration_ms={duration_ms:.2f}"
        )

        return PlanExecutionResult(
            plan_id=plan.plan_id,
            success=success_status,
            final_response=final_text,
            plan_status=plan.status,
            steps_total=len(plan.steps),
            steps_completed=steps_completed,
            steps_failed=steps_failed,
            observations=observations,
            metrics=metrics,
            metadata={}
        )

    def _get_bounded_observations(self, observations: List[StepObservation]) -> List[StepObservation]:
        """Filters observations to fit inside context window character limit defaults."""
        max_chars = settings.planning_max_observation_characters
        total_chars = 0
        selected: List[StepObservation] = []

        # Iterate in reverse order to include the most recent observations
        for obs in reversed(observations):
            content_len = len(obs.content)
            if not selected:
                # Include the latest observation whole
                selected.append(obs)
                total_chars += content_len
            else:
                if total_chars + content_len <= max_chars:
                    selected.append(obs)
                    total_chars += content_len
                else:
                    break

        selected.reverse()  # Restore original chronological order
        return selected

    def _synthesize_failure(
        self,
        original_request_text: str,
        failed_step: Any,
        reason: str,
        observations: List[StepObservation]
    ) -> str:
        """Formulates a clean user-facing failure response summary."""
        try:
            successful_obs = [o for o in observations if o.success]
            prompt = FAILURE_SYNTHESIS_PROMPT.format(
                request=original_request_text,
                failed_step_description=failed_step.description,
                failure_reason=reason,
                successful_observations="\n\n".join(
                    f"Step {o.step_sequence}: {o.content}"
                    for o in successful_obs
                )
            )
            messages = [{"role": "user", "content": prompt}]
            
            gen_result = self._llm_manager.generate(
                messages,
                profile=GenerationProfile.BALANCED,
                priority=InferencePriority.FOREGROUND
            )
            return self._extract_text(gen_result)
        except Exception as e:
            logger.error(f"Failure synthesis failed: {e}")
            return "I couldn't complete the requested task because a required step failed."

    def _extract_text(self, gen_result: Any) -> str:
        """Helper to safely parse and extract text content from GenerationResult."""
        from app.ai.parser import ResponseParser
        parser = ResponseParser()
        return parser.parse_response(gen_result).text.strip()
