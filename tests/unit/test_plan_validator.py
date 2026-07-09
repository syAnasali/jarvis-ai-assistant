"""Unit tests for PlanValidator."""

import pytest
from datetime import datetime, timezone
from app.core.exceptions import PlanValidationError
from app.tools.registry import ToolRegistry
from app.tools.builtin.system import CurrentTimeTool
from app.planning.models import TaskPlan, PlanStep, StepType, StepStatus, PlanStatus
from app.planning.validator import PlanValidator


@pytest.fixture
def registry() -> ToolRegistry:
    """Fixture returning a ToolRegistry with get_current_time registered."""
    reg = ToolRegistry()
    reg.register(CurrentTimeTool())
    return reg


@pytest.fixture
def validator(registry) -> PlanValidator:
    """Fixture returning a PlanValidator instance."""
    return PlanValidator(registry)


def test_validator_valid_plan(validator):
    """Verify validating a structurally and semantically correct plan."""
    steps = [
        PlanStep("s1", 1, "Fetch time", StepType.TOOL, "get_current_time"),
        PlanStep("s2", 2, "Analyze findings", StepType.REASONING),
        PlanStep("s3", 3, "Report", StepType.SYNTHESIS)
    ]
    plan = TaskPlan("p1", "Test goal", steps, PlanStatus.CREATED, datetime.now(timezone.utc))
    validator.validate(plan)  # Should not raise any exceptions


def test_validator_empty_goal(validator):
    """Verify validation fails if plan goal is empty."""
    steps = [PlanStep("s1", 1, "Report", StepType.SYNTHESIS)]
    with pytest.raises(PlanValidationError, match="goal must not be empty"):
        TaskPlan("p1", "  ", steps, PlanStatus.CREATED, datetime.now(timezone.utc))


def test_validator_empty_steps(validator):
    """Verify validation fails if plan steps list is empty."""
    plan = TaskPlan("p1", "Goal", [], PlanStatus.CREATED, datetime.now(timezone.utc))
    with pytest.raises(PlanValidationError, match="Plan must contain at least one step"):
        validator.validate(plan)


def test_validator_step_limit(validator):
    """Verify validator respects maximum plan step count limit (default 8)."""
    steps = [
        PlanStep(f"s{i}", i, "step", StepType.TOOL, "get_current_time")
        for i in range(1, 9)
    ]
    # Add 9th synthesis step
    steps.append(PlanStep("s9", 9, "final", StepType.SYNTHESIS))
    plan = TaskPlan("p1", "Goal", steps, PlanStatus.CREATED, datetime.now(timezone.utc))
    
    with pytest.raises(PlanValidationError, match="exceeds maximum configured limit"):
        validator.validate(plan)


def test_validator_sequence_starts_at_1(validator):
    """Verify sequence starts at 1, rejecting gaps or offset starts."""
    steps = [
        PlanStep("s1", 2, "Report", StepType.SYNTHESIS)
    ]
    plan = TaskPlan("p1", "Goal", steps, PlanStatus.CREATED, datetime.now(timezone.utc))
    with pytest.raises(PlanValidationError, match="sequences must start at 1"):
        validator.validate(plan)


def test_validator_sequence_gaps(validator):
    """Verify sequence gaps are rejected (e.g. 1, 3)."""
    steps = [
        PlanStep("s1", 1, "Fetch time", StepType.TOOL, "get_current_time"),
        PlanStep("s2", 3, "Report", StepType.SYNTHESIS)
    ]
    plan = TaskPlan("p1", "Goal", steps, PlanStatus.CREATED, datetime.now(timezone.utc))
    with pytest.raises(PlanValidationError, match="sequences must be contiguous"):
        validator.validate(plan)


def test_validator_duplicate_sequence(validator):
    """Verify duplicate sequence numbers are rejected."""
    steps = [
        PlanStep("s1", 1, "Fetch time", StepType.TOOL, "get_current_time"),
        PlanStep("s2", 1, "Report", StepType.SYNTHESIS)
    ]
    plan = TaskPlan("p1", "Goal", steps, PlanStatus.CREATED, datetime.now(timezone.utc))
    with pytest.raises(PlanValidationError, match="Duplicate sequence numbers found"):
        validator.validate(plan)


def test_validator_duplicate_step_ids(validator):
    """Verify duplicate step IDs are rejected."""
    steps = [
        PlanStep("s_dup", 1, "Fetch time", StepType.TOOL, "get_current_time"),
        PlanStep("s_dup", 2, "Report", StepType.SYNTHESIS)
    ]
    plan = TaskPlan("p1", "Goal", steps, PlanStatus.CREATED, datetime.now(timezone.utc))
    with pytest.raises(PlanValidationError, match="Duplicate step ID found"):
        validator.validate(plan)


def test_validator_empty_description(validator):
    """Verify step description must be non-empty."""
    with pytest.raises(PlanValidationError, match="description must not be empty"):
        PlanStep("s1", 1, "   ", StepType.SYNTHESIS)


def test_validator_unknown_tool(validator):
    """Verify validator rejects TOOL steps requesting unregistered tools."""
    steps = [
        PlanStep("s1", 1, "Fetch time", StepType.TOOL, "unregistered_tool_name"),
        PlanStep("s2", 2, "Report", StepType.SYNTHESIS)
    ]
    plan = TaskPlan("p1", "Goal", steps, PlanStatus.CREATED, datetime.now(timezone.utc))
    with pytest.raises(PlanValidationError, match="requests unregistered tool"):
        validator.validate(plan)


def test_validator_missing_synthesis(validator):
    """Verify a plan must contain at least one SYNTHESIS step."""
    steps = [
        PlanStep("s1", 1, "Fetch time", StepType.TOOL, "get_current_time"),
        PlanStep("s2", 2, "Reason", StepType.REASONING)
    ]
    plan = TaskPlan("p1", "Goal", steps, PlanStatus.CREATED, datetime.now(timezone.utc))
    with pytest.raises(PlanValidationError, match="must contain exactly one SYNTHESIS step"):
        validator.validate(plan)


def test_validator_multiple_synthesis(validator):
    """Verify a plan must not contain multiple SYNTHESIS steps."""
    steps = [
        PlanStep("s1", 1, "Synthesis 1", StepType.SYNTHESIS),
        PlanStep("s2", 2, "Synthesis 2", StepType.SYNTHESIS)
    ]
    plan = TaskPlan("p1", "Goal", steps, PlanStatus.CREATED, datetime.now(timezone.utc))
    with pytest.raises(PlanValidationError, match="must contain exactly one SYNTHESIS step. Found multiple"):
        validator.validate(plan)


def test_validator_synthesis_not_final(validator):
    """Verify the SYNTHESIS step must be placed at the final sequence position."""
    steps = [
        PlanStep("s1", 1, "Report", StepType.SYNTHESIS),
        PlanStep("s2", 2, "Fetch time", StepType.TOOL, "get_current_time")
    ]
    plan = TaskPlan("p1", "Goal", steps, PlanStatus.CREATED, datetime.now(timezone.utc))
    with pytest.raises(PlanValidationError, match="SYNTHESIS step must be the final step in the plan"):
        validator.validate(plan)


def test_validator_invalid_initial_statuses(validator):
    """Verify validation fails if plan status is not CREATED or VALIDATED."""
    steps = [PlanStep("s1", 1, "Report", StepType.SYNTHESIS)]
    plan = TaskPlan("p1", "Goal", steps, PlanStatus.RUNNING, datetime.now(timezone.utc))
    with pytest.raises(PlanValidationError, match="Invalid initial plan status"):
        validator.validate(plan)

    # Step status not PENDING
    steps_non_pending = [
        PlanStep("s1", 1, "Report", StepType.SYNTHESIS, status=StepStatus.COMPLETED)
    ]
    plan_2 = TaskPlan("p1", "Goal", steps_non_pending, PlanStatus.CREATED, datetime.now(timezone.utc))
    with pytest.raises(PlanValidationError, match="must start with status PENDING"):
        validator.validate(plan_2)
