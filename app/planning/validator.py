"""Validator for structured task plans."""

from app.core.exceptions import PlanValidationError
from app.config.settings import settings
from app.tools.registry import ToolRegistry
from app.planning.models import TaskPlan, PlanStatus, StepStatus, StepType


class PlanValidator:
    """Validates structural and semantic constraints of formulated task plans."""

    def __init__(self, registry: ToolRegistry | None = None) -> None:
        """Initializes the PlanValidator.

        Args:
            registry: Optional ToolRegistry containing registered tools.
        """
        self._registry = registry

    def validate(self, plan: TaskPlan) -> None:
        """Validates all constraints of a TaskPlan.

        Args:
            plan: The TaskPlan object to validate.

        Raises:
            PlanValidationError: If any constraint validation fails.
        """
        # Validate Plan ID
        if not plan.plan_id or not plan.plan_id.strip():
            raise PlanValidationError("Plan ID must not be empty.")

        # Validate Goal
        if not plan.goal or not plan.goal.strip():
            raise PlanValidationError("Plan goal must not be empty.")

        # Validate Steps exist
        if not plan.steps:
            raise PlanValidationError("Plan must contain at least one step.")

        # Validate Max steps count
        max_steps = settings.planning_max_steps
        if len(plan.steps) > max_steps:
            raise PlanValidationError(
                f"Plan step count {len(plan.steps)} exceeds maximum configured limit of {max_steps}."
            )

        # Validate initial plan status
        if plan.status not in (PlanStatus.CREATED, PlanStatus.VALIDATED):
            raise PlanValidationError(f"Invalid initial plan status: {plan.status}")

        step_ids = set()
        sequences = []

        for idx, step in enumerate(plan.steps):
            # Step ID uniqueness
            if not step.step_id or not step.step_id.strip():
                raise PlanValidationError(f"Step at index {idx} has an empty Step ID.")
            if step.step_id in step_ids:
                raise PlanValidationError(f"Duplicate step ID found: {step.step_id}")
            step_ids.add(step.step_id)

            # Step description
            if not step.description or not step.description.strip():
                raise PlanValidationError(f"Step '{step.step_id}' has an empty description.")

            # Step type validation
            if not isinstance(step.step_type, StepType):
                raise PlanValidationError(f"Step '{step.step_id}' has an invalid StepType.")

            # Step status validation
            if step.status != StepStatus.PENDING:
                raise PlanValidationError(f"Step '{step.step_id}' must start with status PENDING, got: {step.status}")

            # TOOL step assertions
            if step.step_type == StepType.TOOL:
                if not step.tool_name or not step.tool_name.strip():
                    raise PlanValidationError(f"TOOL step '{step.step_id}' is missing tool_name.")
                if not isinstance(step.tool_arguments, dict):
                    raise PlanValidationError(f"TOOL step '{step.step_id}' arguments must be a dictionary.")
                if self._registry is not None:
                    if not self._registry.has(step.tool_name):
                        raise PlanValidationError(f"TOOL step '{step.step_id}' requests unregistered tool: '{step.tool_name}'")

            # REASONING and SYNTHESIS assertions
            else:
                if step.tool_name is not None:
                    raise PlanValidationError(f"{step.step_type.name} step '{step.step_id}' must not have a tool_name.")

            sequences.append(step.sequence)

        # Validate sequence numbering
        sequences_sorted = sorted(sequences)
        if not sequences_sorted:
            raise PlanValidationError("Plan sequences must not be empty.")

        # Must start at 1
        if sequences_sorted[0] != 1:
            raise PlanValidationError(f"Plan sequences must start at 1, got: {sequences_sorted[0]}")

        # Must be unique
        if len(sequences_sorted) != len(set(sequences_sorted)):
            raise PlanValidationError("Duplicate sequence numbers found in plan steps.")

        # Must be contiguous (1, 2, 3, ...)
        for i in range(len(sequences_sorted)):
            expected = i + 1
            actual = sequences_sorted[i]
            if actual != expected:
                raise PlanValidationError(f"Plan sequences must be contiguous. Expected {expected}, got {actual}.")

        # Find the synthesis step
        synthesis_steps = [s for s in plan.steps if s.step_type == StepType.SYNTHESIS]
        if not synthesis_steps:
            raise PlanValidationError("Plan must contain exactly one SYNTHESIS step.")
        if len(synthesis_steps) > 1:
            raise PlanValidationError("Plan must contain exactly one SYNTHESIS step. Found multiple.")

        # SYNTHESIS step must be the final step (highest sequence number)
        # Note: since sequences are contiguous starting at 1, the final step sequence is len(plan.steps)
        synthesis_step = synthesis_steps[0]
        final_sequence = len(plan.steps)
        if synthesis_step.sequence != final_sequence:
            raise PlanValidationError(
                f"The SYNTHESIS step must be the final step in the plan (sequence {final_sequence}), got: {synthesis_step.sequence}"
            )
