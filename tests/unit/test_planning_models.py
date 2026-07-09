"""Unit tests for task planning domain models."""

import pytest
from datetime import datetime, timezone
from app.core.exceptions import PlanValidationError
from app.planning.models import (
    ExecutionMode,
    StepType,
    StepStatus,
    PlanStatus,
    PlanningDecision,
    PlanStep,
    TaskPlan,
    StepObservation,
    PlanExecutionResult,
)


def test_execution_mode_values():
    """Verify that ExecutionMode enum has correct values."""
    assert ExecutionMode.DIRECT.value == "direct"
    assert ExecutionMode.PLANNED.value == "planned"


def test_planning_decision_validation():
    """Verify PlanningDecision validates confidence bounds and metadata defensive copy."""
    # Valid creation
    meta = {"key": "val"}
    decision = PlanningDecision(
        mode=ExecutionMode.PLANNED,
        confidence=0.8,
        reason="complex prompt",
        metadata=meta
    )
    assert decision.mode == ExecutionMode.PLANNED
    assert decision.confidence == 0.8
    assert decision.reason == "complex prompt"
    assert decision.metadata == meta
    
    # Verify metadata is deep copied
    meta["key"] = "mutated"
    assert decision.metadata["key"] == "val"

    # Invalid confidence lower bound
    with pytest.raises(PlanValidationError, match="Confidence score must be between 0.0 and 1.0"):
        PlanningDecision(mode=ExecutionMode.PLANNED, confidence=-0.1, reason="reason")

    # Invalid confidence upper bound
    with pytest.raises(PlanValidationError, match="Confidence score must be between 0.0 and 1.0"):
        PlanningDecision(mode=ExecutionMode.PLANNED, confidence=1.1, reason="reason")

    # Empty reason
    with pytest.raises(PlanValidationError, match="reason must not be empty"):
        PlanningDecision(mode=ExecutionMode.PLANNED, confidence=0.5, reason="")


def test_plan_step_valid_creation():
    """Verify PlanStep creates correctly and validates constraints."""
    args = {"arg1": "val1"}
    step = PlanStep(
        step_id="step_1",
        sequence=1,
        description="Run tool",
        step_type=StepType.TOOL,
        tool_name="get_current_time",
        tool_arguments=args,
        status=StepStatus.PENDING
    )
    assert step.step_id == "step_1"
    assert step.sequence == 1
    assert step.description == "Run tool"
    assert step.step_type == StepType.TOOL
    assert step.tool_name == "get_current_time"
    assert step.tool_arguments == args
    assert step.status == StepStatus.PENDING

    # Verify tool arguments deep copied
    args["arg1"] = "mutated"
    assert step.tool_arguments["arg1"] == "val1"

    # Non-TOOL step with tool name set must raise validation error
    with pytest.raises(PlanValidationError, match="must not specify a tool_name"):
        PlanStep(
            step_id="step_2",
            sequence=2,
            description="Reasoning step",
            step_type=StepType.REASONING,
            tool_name="some_tool"
        )

    # TOOL step with missing tool name must raise validation error
    with pytest.raises(PlanValidationError, match="TOOL step type must specify a tool_name"):
        PlanStep(
            step_id="step_3",
            sequence=3,
            description="Tool step with no name",
            step_type=StepType.TOOL,
            tool_name=None
        )

    # Invalid sequence validation
    with pytest.raises(PlanValidationError, match="Sequence number must be a positive integer"):
        PlanStep(
            step_id="step_4",
            sequence=0,
            description="description",
            step_type=StepType.SYNTHESIS
        )


def test_task_plan_timezone_awareness():
    """Verify TaskPlan enforces timezone-aware datetimes."""
    step = PlanStep(
        step_id="step_1",
        sequence=1,
        description="Synthesis",
        step_type=StepType.SYNTHESIS
    )

    # Valid timezone-aware datetime
    now_aware = datetime.now(timezone.utc)
    plan = TaskPlan(
        plan_id="plan_1",
        goal="testing",
        steps=[step],
        status=PlanStatus.CREATED,
        created_at=now_aware
    )
    assert plan.plan_id == "plan_1"
    assert plan.created_at == now_aware

    # Naive datetime rejected
    now_naive = datetime.now()
    with pytest.raises(PlanValidationError, match="created_at must be a timezone-aware datetime"):
        TaskPlan(
            plan_id="plan_1",
            goal="testing",
            steps=[step],
            status=PlanStatus.CREATED,
            created_at=now_naive
        )


def test_step_observation_timezone_awareness():
    """Verify StepObservation enforces timezone-aware datetimes."""
    now_aware = datetime.now(timezone.utc)
    obs = StepObservation(
        step_id="step_1",
        step_sequence=1,
        step_type=StepType.TOOL,
        success=True,
        content="some observation",
        created_at=now_aware
    )
    assert obs.created_at == now_aware

    now_naive = datetime.now()
    with pytest.raises(PlanValidationError, match="created_at must be a timezone-aware datetime"):
        StepObservation(
            step_id="step_1",
            step_sequence=1,
            step_type=StepType.TOOL,
            success=True,
            content="some observation",
            created_at=now_naive
        )
