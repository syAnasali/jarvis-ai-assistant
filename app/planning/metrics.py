"""Metrics for tracking planning and multi-step execution performance."""

from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass(frozen=True)
class PlanningMetrics:
    """Performance metrics for plan formulation and step execution."""

    execution_mode: str
    routing_confidence: float
    planning_duration_ms: float = 0.0
    plan_steps_total: int = 0
    tool_steps: int = 0
    reasoning_steps: int = 0
    synthesis_steps: int = 0
    steps_completed: int = 0
    steps_failed: int = 0
    steps_skipped: int = 0
    tool_calls: int = 0
    reasoning_model_calls: int = 0
    synthesis_model_calls: int = 0
    total_execution_duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
