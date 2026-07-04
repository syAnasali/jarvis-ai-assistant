"""Unit tests for AgentRunner."""

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
        tools: List[Dict[str, Any]] | None = None
    ) -> Any:
        self.calls.append((messages, tools))
        if self.responses:
            return self.responses.pop(0)
        return {"message": {"role": "assistant", "content": "Default final response"}}

    def generate_stream(
        self,
        messages: List[Dict[str, Any]],
        options: Dict[str, Any] | None = None,
        tools: List[Dict[str, Any]] | None = None
    ) -> Any:
        self.calls.append((messages, tools))
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
    """Verifies that normal dialogue with no tool requests returns directly."""
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


def test_agent_runner_requests_safe_tool_execution():
    """Verifies that SAFE tools execute and results return to the model in a second turn."""
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

    # Verify messages passed to the second generate call contains the tool results
    second_call_messages = provider.calls[1][0]
    assert second_call_messages[1]["role"] == "assistant"
    assert second_call_messages[2]["role"] == "tool"
    assert second_call_messages[2]["name"] == "safe_test"
    assert "result_val" in second_call_messages[2]["content"]


def test_agent_runner_multiple_tool_calls_in_one_turn():
    """Verifies executing multiple tool requests in a single LLM turn."""
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

    # Second call should have assistant turn + 2 tool turns (total 4 messages in history)
    second_call_messages = provider.calls[1][0]
    assert len(second_call_messages) == 4
    assert second_call_messages[2]["role"] == "tool"
    assert second_call_messages[3]["role"] == "tool"


def test_agent_runner_confirmation_blocked():
    """Verifies that CONFIRMATION tools block and return failure to model."""
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
    second_call_messages = provider.calls[1][0]
    # Check that tool returned error
    assert "requires confirmation" in second_call_messages[2]["content"]


def test_agent_runner_restricted_blocked():
    """Verifies that RESTRICTED tools block and return failure to model."""
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
    second_call_messages = provider.calls[1][0]
    assert "restricted tools" in second_call_messages[2]["content"]


def test_agent_runner_tool_failure_returned_safely():
    """Verifies that runtime failures in execution return failures back to model."""
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
    second_call_messages = provider.calls[1][0]
    assert "Failure injection" in second_call_messages[2]["content"]


def test_agent_runner_iteration_limit():
    """Verifies that the runner throws an LLMError when loop runs indefinitely."""
    provider = FakeProvider()
    # Always requests a tool call, never terminates
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
    # The max iterations constant is 5, so it should call generate exactly 5 times.
    assert len(provider.calls) == 5
