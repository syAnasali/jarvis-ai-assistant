"""Unit tests for TaskExecutor using simulated dependencies."""

import pytest
from typing import Any
from unittest.mock import MagicMock
from datetime import datetime, timezone
from app.core.exceptions import PlanLimitError, PlanExecutionError, ToolExecutionError
from app.ai.manager import LLMManager
from app.ai.models import GenerationResult, GenerationMetrics
from app.tools.registry import ToolRegistry
from app.tools.executor import ToolExecutor
from app.tools.base import BaseTool
from app.tools.models import ToolPermission, ToolResult
from app.agent.models import ToolCall
from app.planning.models import TaskPlan, PlanStep, StepType, PlanStatus, StepStatus
from app.planning.executor import TaskExecutor


class FakeSafeTool(BaseTool):
    """Fake SAFE tool that always returns success."""
    name: str = "safe_tool"
    description: str = "A safe test tool"
    permission_level: ToolPermission = ToolPermission.SAFE

    def execute(self, **kwargs: Any) -> Any:
        return "safe_tool_output"

    def get_schema(self) -> dict:
        return {"name": self.name, "description": self.description, "parameters": {}}


class FakeConfirmTool(BaseTool):
    """Fake CONFIRMATION tool."""
    name: str = "confirm_tool"
    description: str = "A confirmation required test tool"
    permission_level: ToolPermission = ToolPermission.CONFIRMATION

    def execute(self, **kwargs: Any) -> Any:
        return "confirm_tool_output"

    def get_schema(self) -> dict:
        return {"name": self.name, "description": self.description, "parameters": {}}


class FakeRestrictedTool(BaseTool):
    """Fake RESTRICTED tool."""
    name: str = "restricted_tool"
    description: str = "A restricted test tool"
    permission_level: ToolPermission = ToolPermission.RESTRICTED

    def execute(self, **kwargs: Any) -> Any:
        return "restricted_tool_output"

    def get_schema(self) -> dict:
        return {"name": self.name, "description": self.description, "parameters": {}}


class FakeFailedTool(BaseTool):
    """Fake SAFE tool that returns failure."""
    name: str = "failed_tool"
    description: str = "A tool that fails execution"
    permission_level: ToolPermission = ToolPermission.SAFE

    def execute(self, **kwargs: Any) -> Any:
        raise ToolExecutionError("failed_tool_error")

    def get_schema(self) -> dict:
        return {"name": self.name, "description": self.description, "parameters": {}}


@pytest.fixture
def registry() -> ToolRegistry:
    """Fixture returning a registry with all fake tools registered."""
    reg = ToolRegistry()
    reg.register(FakeSafeTool())
    reg.register(FakeConfirmTool())
    reg.register(FakeRestrictedTool())
    reg.register(FakeFailedTool())
    return reg


@pytest.fixture
def tool_executor(registry) -> ToolExecutor:
    """Fixture returning a real ToolExecutor bound to the fake tools registry."""
    return ToolExecutor(registry)


@pytest.fixture
def llm_manager() -> LLMManager:
    """Fixture returning a mocked LLMManager."""
    mock = MagicMock(spec=LLMManager)
    
    def generate_mock(messages, profile=None, priority=None):
        prompt_text = " ".join([m["content"] for m in messages]).lower()
        if "final response" in prompt_text or "helpful assistant writing" in prompt_text:
            text = "Synthesis response summary."
        elif "logical analyst" in prompt_text or "reasoning" in prompt_text:
            text = "Reasoning analysis conclusion."
        elif "explaining a task execution failure" in prompt_text or "failure" in prompt_text:
            text = "Synthesized failure explanation."
        else:
            text = "Fallback fake response."
            
        metrics = GenerationMetrics(
            provider="fake_llm",
            model="qwen3:8b",
            total_duration_ms=10.0,
            load_duration_ms=0.0,
            prompt_eval_duration_ms=5.0,
            generation_duration_ms=5.0,
            prompt_tokens=10,
            generated_tokens=20,
            tokens_per_second=2000.0,
            generation_profile=profile.value if profile else "BALANCED",
            metadata={}
        )
        return GenerationResult(raw_response=text, metrics=metrics)
        
    mock.generate.side_effect = generate_mock
    return mock


def test_executor_successful_plan(llm_manager, registry, tool_executor):
    """Verify executing a successful plan containing TOOL, REASONING, and SYNTHESIS steps."""
    steps = [
        PlanStep("s1", 1, "Run safe tool", StepType.TOOL, "safe_tool"),
        PlanStep("s2", 2, "Analyze observation", StepType.REASONING),
        PlanStep("s3", 3, "Report final answer", StepType.SYNTHESIS)
    ]
    plan = TaskPlan("p1", "Test plan goal", steps, PlanStatus.CREATED, datetime.now(timezone.utc))

    executor = TaskExecutor(llm_manager, registry, tool_executor)
    result = executor.execute(plan, "Original request")

    # Verify status transitions
    assert plan.status == PlanStatus.COMPLETED
    assert result.success is True
    assert result.final_response == "Synthesis response summary."
    assert result.steps_total == 3
    assert result.steps_completed == 3
    assert result.steps_failed == 0
    assert len(result.observations) == 3

    # Verify steps status
    assert steps[0].status == StepStatus.COMPLETED
    assert steps[1].status == StepStatus.COMPLETED
    assert steps[2].status == StepStatus.COMPLETED

    # Verify observations
    obs1 = result.observations[0]
    assert obs1.step_sequence == 1
    assert obs1.success is True
    assert obs1.content == "safe_tool_output"
    assert obs1.tool_name == "safe_tool"
    assert obs1.created_at.tzinfo == timezone.utc

    obs2 = result.observations[1]
    assert obs2.step_sequence == 2
    assert obs2.success is True
    assert obs2.content == "Reasoning analysis conclusion."

    obs3 = result.observations[2]
    assert obs3.success is True
    assert obs3.content == "Synthesis response summary."

    # Verify metrics
    assert result.metrics.execution_mode == "planned"
    assert result.metrics.tool_calls == 1
    assert result.metrics.reasoning_model_calls == 1
    assert result.metrics.synthesis_model_calls == 1


def test_executor_blocked_confirmation_tool(llm_manager, registry, tool_executor):
    """Verify planned CONFIRMATION tools remain blocked and cause execution failure."""
    steps = [
        PlanStep("s1", 1, "Run confirm tool", StepType.TOOL, "confirm_tool"),
        PlanStep("s2", 2, "Report final answer", StepType.SYNTHESIS)
    ]
    plan = TaskPlan("p1", "Goal", steps, PlanStatus.CREATED, datetime.now(timezone.utc))

    executor = TaskExecutor(llm_manager, registry, tool_executor)
    result = executor.execute(plan, "Original request")

    assert plan.status == PlanStatus.FAILED
    assert result.success is False
    assert result.final_response == "Synthesized failure explanation."
    assert result.steps_completed == 0
    assert result.steps_failed == 1
    assert result.metrics.steps_skipped == 1
    
    assert steps[0].status == StepStatus.FAILED
    assert steps[1].status == StepStatus.SKIPPED


def test_executor_blocked_restricted_tool(llm_manager, registry, tool_executor):
    """Verify planned RESTRICTED tools remain blocked and cause execution failure."""
    steps = [
        PlanStep("s1", 1, "Run restricted tool", StepType.TOOL, "restricted_tool"),
        PlanStep("s2", 2, "Report final answer", StepType.SYNTHESIS)
    ]
    plan = TaskPlan("p1", "Goal", steps, PlanStatus.CREATED, datetime.now(timezone.utc))

    executor = TaskExecutor(llm_manager, registry, tool_executor)
    result = executor.execute(plan, "Original request")

    assert plan.status == PlanStatus.FAILED
    assert result.success is False
    assert result.final_response == "Synthesized failure explanation."
    assert result.steps_completed == 0
    assert result.steps_failed == 1
    assert result.metrics.steps_skipped == 1
    
    assert steps[0].status == StepStatus.FAILED
    assert steps[1].status == StepStatus.SKIPPED


def test_executor_tool_failure_branches(llm_manager, registry, tool_executor):
    """Verify execution halts immediately on tool failure, skipping subsequent steps."""
    steps = [
        PlanStep("s1", 1, "Run failing tool", StepType.TOOL, "failed_tool"),
        PlanStep("s2", 2, "Reason step", StepType.REASONING),
        PlanStep("s3", 3, "Report final answer", StepType.SYNTHESIS)
    ]
    plan = TaskPlan("p1", "Goal", steps, PlanStatus.CREATED, datetime.now(timezone.utc))

    executor = TaskExecutor(llm_manager, registry, tool_executor)
    result = executor.execute(plan, "Original request")

    assert plan.status == PlanStatus.FAILED
    assert result.success is False
    assert result.final_response == "Synthesized failure explanation."
    assert result.steps_completed == 0
    assert result.steps_failed == 1
    assert result.metrics.steps_skipped == 2
    
    assert steps[0].status == StepStatus.FAILED
    assert steps[1].status == StepStatus.SKIPPED
    assert steps[2].status == StepStatus.SKIPPED


def test_executor_step_limit_enforced_by_executor(llm_manager, registry, tool_executor):
    """Verify TaskExecutor raises PlanLimitError if step limit is exceeded at runtime."""
    # Build 9 steps
    steps = [
        PlanStep(f"s{i}", i, "step", StepType.TOOL, "safe_tool")
        for i in range(1, 9)
    ]
    steps.append(PlanStep("s9", 9, "synthesize", StepType.SYNTHESIS))
    plan = TaskPlan("p1", "Goal", steps, PlanStatus.CREATED, datetime.now(timezone.utc))

    executor = TaskExecutor(llm_manager, registry, tool_executor)
    with pytest.raises(PlanLimitError, match="Plan exceeds the maximum limit"):
        executor.execute(plan, "Original request")


def test_executor_synthesis_failure_fallback(registry, tool_executor):
    """Verify synthesis failure triggers a deterministic fallback string."""
    mock_llm = MagicMock(spec=LLMManager)
    # Force model call failure
    mock_llm.generate.side_effect = RuntimeError("Generation model crash")

    steps = [
        PlanStep("s1", 1, "Run failing tool", StepType.TOOL, "failed_tool"),
        PlanStep("s2", 2, "Report final answer", StepType.SYNTHESIS)
    ]
    plan = TaskPlan("p1", "Goal", steps, PlanStatus.CREATED, datetime.now(timezone.utc))

    executor = TaskExecutor(mock_llm, registry, tool_executor)
    result = executor.execute(plan, "Original request")

    assert plan.status == PlanStatus.FAILED
    assert result.success is False
    # Verifies deterministic fallback response string is returned
    assert result.final_response == "I couldn't complete the requested task because a required step failed."
