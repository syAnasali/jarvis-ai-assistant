"""Request tracing and execution timeline instrumentation module."""

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.core.logger import JarvisLogger

logger = JarvisLogger.get_logger("performance")


@dataclass
class TimelineStage:
    """Represents a single execution stage within a request timeline."""

    stage_name: str
    start_time: float
    end_time: float = 0.0
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def complete(self) -> None:
        """Marks stage completion and calculates elapsed duration in milliseconds."""
        self.end_time = time.perf_counter()
        self.duration_ms = (self.end_time - self.start_time) * 1000.0


class RequestTracer:
    """Traces lifecycle stages, latencies, and execution timeline for a single request."""

    def __init__(self, request_id: str, session_id: Optional[str] = None) -> None:
        """Initializes a new RequestTracer instance."""
        self.request_id = request_id
        self.session_id = session_id or "unknown"
        self.start_perf_time = time.perf_counter()
        self.start_wall_time = datetime.now(timezone.utc)
        self.stages: List[TimelineStage] = []
        self._active_stages: Dict[str, TimelineStage] = {}
        self.metrics: Dict[str, float] = {
            "planner_latency_ms": 0.0,
            "memory_retrieval_latency_ms": 0.0,
            "memory_write_latency_ms": 0.0,
            "prompt_construction_duration_ms": 0.0,
            "llm_latency_ms": 0.0,
            "streaming_latency_ms": 0.0,
            "tool_execution_duration_ms": 0.0,
            "approval_wait_duration_ms": 0.0,
            "conversation_persistence_duration_ms": 0.0,
            "total_duration_ms": 0.0,
        }

    def start_stage(self, stage_name: str, metadata: Optional[Dict[str, Any]] = None) -> TimelineStage:
        """Starts timing an execution stage."""
        stage = TimelineStage(
            stage_name=stage_name,
            start_time=time.perf_counter(),
            metadata=metadata or {}
        )
        self._active_stages[stage_name] = stage
        return stage

    def end_stage(self, stage_name: str, metadata: Optional[Dict[str, Any]] = None) -> float:
        """Completes timing an execution stage and records its duration."""
        stage = self._active_stages.pop(stage_name, None)
        if not stage:
            return 0.0
        stage.complete()
        if metadata:
            stage.metadata.update(metadata)
        self.stages.append(stage)

        # Structured log for timeline event
        logger.log_event(
            action=f"Timeline stage: {stage_name}",
            status="completed",
            duration_ms=stage.duration_ms,
            request_id=self.request_id,
            session_id=self.session_id,
            metadata=stage.metadata
        )
        return stage.duration_ms

    def record_metric(self, metric_name: str, duration_ms: float) -> None:
        """Accumulates a specific performance metric."""
        if metric_name in self.metrics:
            self.metrics[metric_name] += duration_ms
        else:
            self.metrics[metric_name] = duration_ms

    def finalize(self) -> float:
        """Finalizes total request execution duration."""
        total_ms = (time.perf_counter() - self.start_perf_time) * 1000.0
        self.metrics["total_duration_ms"] = total_ms
        return total_ms

    def get_performance_summary(self) -> str:
        """Returns a human-readable concise performance summary string."""
        lines = [
            f"=== Performance Summary [Request ID: {self.request_id}] ===",
            f"  Total Request Duration:           {self.metrics['total_duration_ms']:.2f} ms",
            f"  Planner Latency:                  {self.metrics['planner_latency_ms']:.2f} ms",
            f"  Memory Retrieval Latency:         {self.metrics['memory_retrieval_latency_ms']:.2f} ms",
            f"  Memory Write Latency:             {self.metrics['memory_write_latency_ms']:.2f} ms",
            f"  Prompt Construction Time:         {self.metrics['prompt_construction_duration_ms']:.2f} ms",
            f"  LLM Latency:                      {self.metrics['llm_latency_ms']:.2f} ms",
            f"  Streaming Latency:                {self.metrics['streaming_latency_ms']:.2f} ms",
            f"  Tool Execution Time:              {self.metrics['tool_execution_duration_ms']:.2f} ms",
            f"  Approval Wait Time:               {self.metrics['approval_wait_duration_ms']:.2f} ms",
            f"  Conversation Persistence Time:    {self.metrics['conversation_persistence_duration_ms']:.2f} ms",
        ]
        return "\n".join(lines)

    def get_prompt_diagnostics_report(
        self,
        messages_used: int = 0,
        messages_skipped: int = 0,
        memory_count: int = 0,
        tool_count: int = 0,
        prompt_chars: int = 0,
        unoptimized_baseline_chars: int = 0
    ) -> str:
        """Generates a prompt diagnostics report.

        Args:
            messages_used: Count of conversation messages used.
            messages_skipped: Count of conversation messages skipped/trimmed.
            memory_count: Count of memories injected.
            tool_count: Count of tool schemas injected.
            prompt_chars: Total character length of active prompt.
            unoptimized_baseline_chars: Baseline prompt character size before optimization.

        Returns:
            str: Formatted Prompt Diagnostics Report.
        """
        estimated_tokens = max(1, prompt_chars // 4)
        reduction_pct = 0.0
        if unoptimized_baseline_chars > 0 and unoptimized_baseline_chars > prompt_chars:
            reduction_pct = ((unoptimized_baseline_chars - prompt_chars) / unoptimized_baseline_chars) * 100.0

        lines = [
            f"=== Prompt Diagnostics Report [Request ID: {self.request_id}] ===",
            f"  Conversation Messages Used:     {messages_used}",
            f"  Conversation Messages Skipped:  {messages_skipped}",
            f"  Injected Memories Count:        {memory_count}",
            f"  Injected Tool Schemas Count:    {tool_count}",
            f"  Total Prompt Size:              {prompt_chars} chars (~{estimated_tokens} tokens)",
            f"  Prompt Reduction vs Baseline:   {reduction_pct:.1f}%",
        ]
        return "\n".join(lines)

    def get_timeline_dict(self) -> List[Dict[str, Any]]:
        """Returns a list representation of all recorded timeline stages."""
        return [
            {
                "stage": s.stage_name,
                "duration_ms": round(s.duration_ms, 2),
                "metadata": s.metadata
            }
            for s in self.stages
        ]
