"""Unit tests for AgentRunner execution metrics, action loops, and generation profiles."""

import pytest
from typing import Any, List, Dict
from app.ai.interfaces import BaseLLMProvider
from app.ai.manager import LLMManager
from app.tools.base import BaseTool
from app.tools.models import ToolPermission
from app.tools.registry import ToolRegistry
from app.tools.executor import ToolExecutor
from app.ai.parser import ResponseParser
from app.agent.runner import AgentRunner
from app.agent.models import AgentRequest, ToolCall
from app.ai.models import GenerationMetrics, GenerationResult, GenerationProfile
from app.ai.prompts import PromptManager, TOOL_USE_POLICY_MARKER
from app.core.exceptions import LLMError


class FakeProvider(BaseLLMProvider):
    """Fake LLM Provider for unit testing."""

    def __init__(self) -> None:
        self.responses: List[Any] = []
        self.stream_responses: List[List[Any]] = []
        self.calls: List[Any] = []

    def initialize(self) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def is_available(self) -> bool:
        return True

    def generate(
        self,
        messages: List[Dict[str, Any]],
        options: Dict[str, Any] | None = None,
        tools: List[Dict[str, Any]] | None = None,
        profile: GenerationProfile = GenerationProfile.BALANCED
    ) -> GenerationResult:
        self.calls.append((messages, tools, profile))
        
        if self.responses:
            raw = self.responses.pop(0)
        else:
            raw = {"message": {"role": "assistant", "content": "Default final response"}}
            
        metrics = GenerationMetrics(
            provider="fake",
            model="fake_model",
            total_duration_ms=10.0,
            load_duration_ms=1.0,
            prompt_eval_duration_ms=2.0,
            generation_duration_ms=7.0,
            prompt_tokens=5,
            generated_tokens=10,
            tokens_per_second=1000.0,
            generation_profile=profile.value
        )
        return GenerationResult(raw_response=raw, metrics=metrics)

    def generate_stream(
        self,
        messages: List[Dict[str, Any]],
        options: Dict[str, Any] | None = None,
        tools: List[Dict[str, Any]] | None = None,
        profile: GenerationProfile = GenerationProfile.BALANCED
    ) -> Any:
        self.calls.append((messages, tools, profile))
        if self.stream_responses:
            return self.stream_responses.pop(0)
        return [{"message": {"role": "assistant", "content": "Default final stream chunk"}}]

    def health_check(self) -> Dict[str, Any]:
        return {}


class SafeTestTool(BaseTool):
    """Safe tool mock for testing agent action loops."""

    @property
    def name(self) -> str:
        return "safe_test"

    @property
    def description(self) -> str:
        return "Safe test tool"

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.SAFE

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "arg": {"type": "string"}
                },
                "required": ["arg"]
            }
        }

    def execute(self, arg: str) -> str:
        if arg == "fail":
            raise ValueError("Failure injection")
        return f"result_{arg}"


class ConfirmationTestTool(BaseTool):
    """Confirmation tool mock for testing executor blocking."""

    @property
    def name(self) -> str:
        return "confirm_test"

    @property
    def description(self) -> str:
        return "Confirmation test tool"

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.CONFIRMATION

    def get_schema(self) -> Dict[str, Any]:
        return {"name": self.name, "description": self.description}

    def execute(self, **kwargs) -> str:
        return "ok"


class RestrictedTestTool(BaseTool):
    """Restricted tool mock for testing executor blocking."""

    @property
    def name(self) -> str:
        return "restricted_test"

    @property
    def description(self) -> str:
        return "Restricted test tool"

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.RESTRICTED

    def get_schema(self) -> Dict[str, Any]:
        return {"name": self.name, "description": self.description}

    def execute(self, **kwargs) -> str:
        return "ok"


def test_agent_runner_normal_response_no_tools():
    """Verifies that normal dialogue uses TOOL_SELECTION profile for the first turn."""
    provider = FakeProvider()
    provider.responses.append({"message": {"role": "assistant", "content": "Hello!"}})

    llm_manager = LLMManager()
    llm_manager.register_provider("fake", provider)
    llm_manager.switch_provider("fake")

    registry = ToolRegistry()
    executor = ToolExecutor(registry)
    parser = ResponseParser()
    runner = AgentRunner(llm_manager, registry, executor, parser)

    req = AgentRequest("r1", "Hi", "terminal")
    res = runner.run(req, [{"role": "user", "content": "Hi"}])

    assert res.text == "Hello!"
    assert len(provider.calls) == 1
    
    # Verify first turn uses TOOL_SELECTION
    messages, tools, profile = provider.calls[0]
    assert profile == GenerationProfile.TOOL_SELECTION
    
    # Assert metrics
    metrics = res.execution_metrics
    assert metrics.iterations == 1
    assert metrics.model_calls == 1
    assert metrics.tool_calls == 0
    assert len(metrics.iteration_metrics) == 1
    assert metrics.iteration_metrics[0].model_metrics.generation_profile == "tool_selection"
    assert res.requested_tools == ()


def test_agent_runner_requests_safe_tool_execution():
    """Verifies that SAFE tool execution tracks model calls, tool calls, and profiles correctly (TOOL_SELECTION then FAST)."""
    provider = FakeProvider()
    # 1st response: requests a tool call
    provider.responses.append({
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "safe_test",
                        "arguments": {"arg": "val"}
                    }
                }
            ]
        }
    })
    # 2nd response: returns final answer
    provider.responses.append({
        "message": {
            "role": "assistant",
            "content": "The tool output was: result_val."
        }
    })

    llm_manager = LLMManager()
    llm_manager.register_provider("fake", provider)
    llm_manager.switch_provider("fake")

    registry = ToolRegistry()
    registry.register(SafeTestTool())
    executor = ToolExecutor(registry)
    parser = ResponseParser()
    runner = AgentRunner(llm_manager, registry, executor, parser)

    req = AgentRequest("r1", "Query", "terminal")
    res = runner.run(req, [{"role": "user", "content": "Query"}])

    assert res.text == "The tool output was: result_val."
    assert len(provider.calls) == 2

    # Verify first turn used GenerationProfile.TOOL_SELECTION and second used GenerationProfile.FAST
    assert provider.calls[0][2] == GenerationProfile.TOOL_SELECTION
    assert provider.calls[1][2] == GenerationProfile.FAST

    # Assert metrics
    metrics = res.execution_metrics
    assert metrics.iterations == 2
    assert metrics.model_calls == 2
    assert metrics.tool_calls == 1
    assert len(metrics.iteration_metrics) == 2
    assert metrics.iteration_metrics[0].tool_calls_count == 1
    assert metrics.iteration_metrics[0].model_metrics.generation_profile == "tool_selection"
    assert metrics.iteration_metrics[1].tool_calls_count == 0
    assert metrics.iteration_metrics[1].model_metrics.generation_profile == "fast"
    assert res.requested_tools == ("safe_test",)


def test_agent_runner_multiple_tool_calls_in_one_turn():
    """Verifies executing multiple tool requests tracks tool call count and profile."""
    provider = FakeProvider()
    provider.responses.append({
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"function": {"name": "safe_test", "arguments": {"arg": "one"}}},
                {"function": {"name": "safe_test", "arguments": {"arg": "two"}}}
            ]
        }
    })
    provider.responses.append({"message": {"role": "assistant", "content": "done"}})

    llm_manager = LLMManager()
    llm_manager.register_provider("fake", provider)
    llm_manager.switch_provider("fake")

    registry = ToolRegistry()
    registry.register(SafeTestTool())
    executor = ToolExecutor(registry)
    parser = ResponseParser()
    runner = AgentRunner(llm_manager, registry, executor, parser)

    req = AgentRequest("r1", "Query", "terminal")
    res = runner.run(req, [{"role": "user", "content": "Query"}])

    assert res.text == "done"
    assert len(provider.calls) == 2
    assert provider.calls[0][2] == GenerationProfile.TOOL_SELECTION
    assert provider.calls[1][2] == GenerationProfile.FAST

    metrics = res.execution_metrics
    assert metrics.iterations == 2
    assert metrics.model_calls == 2
    assert metrics.tool_calls == 2
    assert metrics.iteration_metrics[0].tool_calls_count == 2
    assert metrics.iteration_metrics[0].model_metrics.generation_profile == "tool_selection"
    assert "safe_test" in res.requested_tools


def test_agent_runner_confirmation_blocked():
    """Verifies that CONFIRMATION tool block is counted."""
    provider = FakeProvider()
    provider.responses.append({
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"function": {"name": "confirm_test", "arguments": {}}}
            ]
        }
    })
    provider.responses.append({"message": {"role": "assistant", "content": "blocked"}})

    llm_manager = LLMManager()
    llm_manager.register_provider("fake", provider)
    llm_manager.switch_provider("fake")

    registry = ToolRegistry()
    registry.register(ConfirmationTestTool())
    executor = ToolExecutor(registry)
    parser = ResponseParser()
    runner = AgentRunner(llm_manager, registry, executor, parser)

    req = AgentRequest("r1", "Query", "terminal")
    res = runner.run(req, [{"role": "user", "content": "Query"}])

    assert res.text == "blocked"
    metrics = res.execution_metrics
    assert metrics.iterations == 2
    assert metrics.model_calls == 2
    assert metrics.tool_calls == 1


def test_agent_runner_restricted_blocked():
    """Verifies that RESTRICTED tool block is counted."""
    provider = FakeProvider()
    provider.responses.append({
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"function": {"name": "restricted_test", "arguments": {}}}
            ]
        }
    })
    provider.responses.append({"message": {"role": "assistant", "content": "blocked"}})

    llm_manager = LLMManager()
    llm_manager.register_provider("fake", provider)
    llm_manager.switch_provider("fake")

    registry = ToolRegistry()
    registry.register(RestrictedTestTool())
    executor = ToolExecutor(registry)
    parser = ResponseParser()
    runner = AgentRunner(llm_manager, registry, executor, parser)

    req = AgentRequest("r1", "Query", "terminal")
    res = runner.run(req, [{"role": "user", "content": "Query"}])

    assert res.text == "blocked"
    metrics = res.execution_metrics
    assert metrics.iterations == 2
    assert metrics.model_calls == 2
    assert metrics.tool_calls == 1


def test_agent_runner_tool_failure_returned_safely():
    """Verifies that tool failure is tracked."""
    provider = FakeProvider()
    provider.responses.append({
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"function": {"name": "safe_test", "arguments": {"arg": "fail"}}}
            ]
        }
    })
    provider.responses.append({"message": {"role": "assistant", "content": "failed"}})

    llm_manager = LLMManager()
    llm_manager.register_provider("fake", provider)
    llm_manager.switch_provider("fake")

    registry = ToolRegistry()
    registry.register(SafeTestTool())
    executor = ToolExecutor(registry)
    parser = ResponseParser()
    runner = AgentRunner(llm_manager, registry, executor, parser)

    req = AgentRequest("r1", "Query", "terminal")
    res = runner.run(req, [{"role": "user", "content": "Query"}])

    assert res.text == "failed"
    metrics = res.execution_metrics
    assert metrics.iterations == 2
    assert metrics.model_calls == 2
    assert metrics.tool_calls == 1


def test_agent_runner_iteration_limit():
    """Verifies that runner triggers limit and iteration metrics remain valid up to 5."""
    provider = FakeProvider()
    for _ in range(10):
        provider.responses.append({
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"function": {"name": "safe_test", "arguments": {"arg": "loop"}}}
                ]
            }
        })

    llm_manager = LLMManager()
    llm_manager.register_provider("fake", provider)
    llm_manager.switch_provider("fake")

    registry = ToolRegistry()
    registry.register(SafeTestTool())
    executor = ToolExecutor(registry)
    parser = ResponseParser()
    runner = AgentRunner(llm_manager, registry, executor, parser)

    req = AgentRequest("r1", "Query", "terminal")
    with pytest.raises(LLMError) as exc_info:
        runner.run(req, [{"role": "user", "content": "Query"}])

    assert "maximum iteration limit" in str(exc_info.value)
    assert len(provider.calls) == 5


def test_agent_runner_injects_tool_use_policy_exactly_once():
    """Verifies that tool policy is present for tool-aware execution and is not duplicated."""
    provider = FakeProvider()
    # 1st response: requests safe_test
    provider.responses.append({
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"function": {"name": "safe_test", "arguments": {"arg": "ok"}}}]
        }
    })
    # 2nd response: final response
    provider.responses.append({"message": {"role": "assistant", "content": "Final response text"}})

    llm_manager = LLMManager()
    llm_manager.register_provider("fake", provider)
    llm_manager.switch_provider("fake")

    registry = ToolRegistry()
    registry.register(SafeTestTool())
    executor = ToolExecutor(registry)
    parser = ResponseParser()
    runner = AgentRunner(llm_manager, registry, executor, parser)

    req = AgentRequest("r1", "Query", "terminal")
    res = runner.run(req, [{"role": "user", "content": "Query"}])

    assert res.text == "Final response text"
    assert len(provider.calls) == 2

    # Check first turn messages
    first_messages = provider.calls[0][0]
    # Check system messages
    system_messages = [msg for msg in first_messages if msg["role"] == "system"]
    assert len(system_messages) == 2
    assert "You are Jarvis" in system_messages[0]["content"]
    assert TOOL_USE_POLICY_MARKER in system_messages[1]["content"]

    # Check second turn messages
    second_messages = provider.calls[1][0]
    # Verify tool policy is still there exactly once
    system_messages = [msg for msg in second_messages if msg["role"] == "system"]
    assert len(system_messages) == 2
    assert "You are Jarvis" in system_messages[0]["content"]
    assert TOOL_USE_POLICY_MARKER in system_messages[1]["content"]


def test_agent_runner_memory_coexistence():
    """Verifies that system prompt, tool-use policy, and memory context coexist correctly and are not duplicated."""
    provider = FakeProvider()
    provider.responses.append({
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"function": {"name": "safe_test", "arguments": {"arg": "ok"}}}]
        }
    })
    provider.responses.append({"message": {"role": "assistant", "content": "Final response text"}})

    llm_manager = LLMManager()
    llm_manager.register_provider("fake", provider)
    llm_manager.switch_provider("fake")

    registry = ToolRegistry()
    registry.register(SafeTestTool())
    executor = ToolExecutor(registry)
    parser = ResponseParser()
    runner = AgentRunner(llm_manager, registry, executor, parser)

    req = AgentRequest("r1", "Query", "terminal")
    mem_ctx = "[RELEVANT LONG-TERM MEMORY]\n- The user's name is Anas."
    res = runner.run(req, [{"role": "user", "content": "Query"}], memory_context=mem_ctx)

    assert res.text == "Final response text"
    assert len(provider.calls) == 2

    # Verify first turn system context order:
    # 1. Core/system instructions
    # 2. Tool-use policy
    # 3. Relevant long-term memory
    first_messages = provider.calls[0][0]
    system_messages = [msg for msg in first_messages if msg["role"] == "system"]
    
    assert len(system_messages) == 3
    assert "You are Jarvis" in system_messages[0]["content"]
    assert TOOL_USE_POLICY_MARKER in system_messages[1]["content"]
    assert "RELEVANT LONG-TERM MEMORY" in system_messages[2]["content"]

    # Verify second turn system context remains same (not duplicated)
    second_messages = provider.calls[1][0]
    system_messages = [msg for msg in second_messages if msg["role"] == "system"]
    
    assert len(system_messages) == 3
    assert "You are Jarvis" in system_messages[0]["content"]
    assert TOOL_USE_POLICY_MARKER in system_messages[1]["content"]
    assert "RELEVANT LONG-TERM MEMORY" in system_messages[2]["content"]
