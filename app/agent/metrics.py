"""Performance and timing metrics models for the agent engine."""

from dataclasses import dataclass, field
from typing import List
from app.ai.models import GenerationMetrics


@dataclass(frozen=True)
class AgentIterationMetrics:
    """Metrics tracking a single execution loop iteration.

    Attributes:
        iteration: The loop turn number index.
        duration_ms: Time spent in this iteration.
        model_metrics: LLM generation metrics.
        tool_calls_count: Number of tools called in this turn.
    """

    iteration: int
    duration_ms: float
    model_metrics: GenerationMetrics | None = None
    tool_calls_count: int = 0


@dataclass(frozen=True)
class AgentExecutionMetrics:
    """Aggregate execution metrics across a full request cycle.

    Attributes:
        total_duration_ms: Time from start to completion.
        iterations: Number of turns executed.
        model_calls: Count of generation requests.
        tool_calls: Count of executed tool calls.
        iteration_metrics: Per-iteration metrics details list.
        requested_tools: tuple of tool names selected during execution.
    """

    total_duration_ms: float
    iterations: int
    model_calls: int
    tool_calls: int
    iteration_metrics: List[AgentIterationMetrics] = field(default_factory=list)
    requested_tools: tuple[str, ...] = ()
    memory_matches: tuple[str, ...] = ()
    memory_retrieval_duration_ms: float = 0.0
    memory_extraction_duration_ms: float = 0.0
    memories_extracted: int = 0
    memories_persisted: int = 0
    pending_action_id: str | None = None
    confirmation_required: bool = False
