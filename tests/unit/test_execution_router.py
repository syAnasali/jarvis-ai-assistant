"""Unit tests for ExecutionRouter."""

import pytest
from app.agent.models import AgentRequest
from app.planning.models import ExecutionMode
from app.planning.router import ExecutionRouter


@pytest.fixture
def router() -> ExecutionRouter:
    """Fixture returning an ExecutionRouter instance."""
    return ExecutionRouter()


@pytest.mark.parametrize(
    "prompt",
    [
        "What time is it?",
        "Tell me about this computer.",
        "Explain photosynthesis.",
        "Respond with exactly OK.",
        "What is my name?",
        "Write a Python function to reverse a string.",
        "Tell me about Python and Java.",
    ]
)
def test_direct_routing_cases(router, prompt):
    """Verify simple requests route to DIRECT mode."""
    req = AgentRequest("r_direct", prompt, "terminal")
    decision = router.route(req)
    assert decision.mode == ExecutionMode.DIRECT
    assert 0.0 <= decision.confidence < 0.5
    assert len(decision.reason) > 0
    # Verify request not mutated
    assert req.text == prompt


@pytest.mark.parametrize(
    "prompt",
    [
        "Check my computer information and current local time, then summarize my environment.",
        "Inspect my system, evaluate whether it looks suitable for Jarvis development, and recommend what I should inspect next.",
        "Check the time and system information, compare the findings, and give me a short report.",
        "Gather system details, evaluate them, and recommend next steps.",
    ]
)
def test_planned_routing_cases(router, prompt):
    """Verify multi-step/reasoning requests route to PLANNED mode."""
    req = AgentRequest("r_planned", prompt, "terminal")
    decision = router.route(req)
    assert decision.mode == ExecutionMode.PLANNED
    assert 0.5 <= decision.confidence <= 1.0
    assert len(decision.reason) > 0


def test_deterministic_repeated_routing(router):
    """Verify that routing decisions are fully deterministic."""
    prompt = "Check the time and system information, compare the findings, and give me a short report."
    req = AgentRequest("r_det", prompt, "terminal")
    
    first = router.route(req)
    for _ in range(5):
        assert router.route(req) == first
