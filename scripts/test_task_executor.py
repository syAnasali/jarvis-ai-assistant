"""Diagnostic script for TaskExecutor with fake LLM and tools."""

import sys
from unittest.mock import MagicMock
from datetime import datetime, timezone
from app.ai.manager import LLMManager
from app.ai.models import GenerationResult, GenerationMetrics
from app.tools.registry import ToolRegistry
from app.tools.executor import ToolExecutor
from app.tools.base import BaseTool
from app.tools.models import ToolPermission, ToolResult
from app.planning.models import TaskPlan, PlanStep, StepType, PlanStatus
from app.planning.executor import TaskExecutor

class FakeTimeTool(BaseTool):
    name: str = "get_current_time"
    description: str = "Time tool"
    permission_level: ToolPermission = ToolPermission.SAFE
    def execute(self, **kwargs) -> str:
        return "12:00:00 UTC"
    def get_schema(self) -> dict:
        return {"name": self.name, "description": self.description, "parameters": {}}

def run_diagnostic():
    print("=== TaskExecutor Diagnostic ===")
    
    registry = ToolRegistry()
    registry.register(FakeTimeTool())
    
    tool_executor = ToolExecutor(registry)
    
    mock_llm = MagicMock(spec=LLMManager)
    def mock_generate(messages, profile=None, priority=None):
        prompt = " ".join([m["content"] for m in messages]).lower()
        if "helpful assistant writing" in prompt or "final response" in prompt:
            text = "Final synthesized report: time is 12:00:00 UTC."
        elif "logical analyst" in prompt or "reasoning" in prompt:
            text = "Analytical reasoning conclusion: time obtained is valid."
        else:
            text = "Fallback"
            
        metrics = GenerationMetrics("fake", "model", total_duration_ms=5.0)
        return GenerationResult(text, metrics)
    mock_llm.generate.side_effect = mock_generate

    steps = [
        PlanStep("s1", 1, "Retrieve current time", StepType.TOOL, "get_current_time"),
        PlanStep("s2", 2, "Analyze time correctness", StepType.REASONING),
        PlanStep("s3", 3, "Formulate final report", StepType.SYNTHESIS)
    ]
    plan = TaskPlan("p1", "Report current system time", steps, PlanStatus.CREATED, datetime.now(timezone.utc))

    executor = TaskExecutor(mock_llm, registry, tool_executor)
    print("Executing plan...")
    result = executor.execute(plan, "What is the time?")
    
    print(f"Execution finished: success={result.success}, status={result.plan_status.name}")
    print(f"Final response: {result.final_response!r}")
    print(f"Completed steps: {result.steps_completed}/{result.steps_total}")
    print(f"Observations count: {len(result.observations)}")
    for obs in result.observations:
        print(f"  Step {obs.step_sequence} ({obs.step_type.name}): {obs.content!r}")

    if not result.success or result.final_response != "Final synthesized report: time is 12:00:00 UTC.":
        print("FAILED: final response mismatch.")
        sys.exit(1)
        
    print("\nDiagnostic completed successfully.")

if __name__ == "__main__":
    run_diagnostic()
