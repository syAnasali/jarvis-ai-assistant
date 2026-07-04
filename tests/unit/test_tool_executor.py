"""Unit tests for ToolExecutor."""

import pytest
from app.tools.base import BaseTool
from app.tools.models import ToolPermission
from app.tools.registry import ToolRegistry
from app.tools.executor import ToolExecutor
from app.agent.models import ToolCall


class SafeTool(BaseTool):
    """Mock BaseTool with SAFE permission level."""

    @property
    def name(self) -> str:
        return "safe_tool"

    @property
    def description(self) -> str:
        return "Safe tool"

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.SAFE

    def get_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "val": {"type": "string"}
                },
                "required": ["val"]
            }
        }

    def execute(self, val: str) -> str:
        if val == "raise":
            raise ValueError("Runtime failure")
        return f"safe_{val}"


class ConfirmationTool(BaseTool):
    """Mock BaseTool with CONFIRMATION permission level."""

    @property
    def name(self) -> str:
        return "confirm_tool"

    @property
    def description(self) -> str:
        return "Confirmation tool"

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.CONFIRMATION

    def get_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }

    def execute(self, **kwargs) -> str:
        return "confirm"


class RestrictedTool(BaseTool):
    """Mock BaseTool with RESTRICTED permission level."""

    @property
    def name(self) -> str:
        return "restricted_tool"

    @property
    def description(self) -> str:
        return "Restricted tool"

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.RESTRICTED

    def get_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }

    def execute(self, **kwargs) -> str:
        return "restricted"


def test_executor_safe_tool_execution():
    """Verifies SAFE permission level tools execute successfully."""
    registry = ToolRegistry()
    registry.register(SafeTool())
    executor = ToolExecutor(registry)
    
    call = ToolCall(tool_name="safe_tool", arguments={"val": "hello"})
    res = executor.execute(call)
    
    assert res.success
    assert res.output == "safe_hello"
    assert res.error is None
    assert res.metadata["permission_level"] == "safe"


def test_executor_confirmation_blocked():
    """Verifies CONFIRMATION permission level tools are blocked from execution."""
    registry = ToolRegistry()
    registry.register(ConfirmationTool())
    executor = ToolExecutor(registry)
    
    call = ToolCall(tool_name="confirm_tool", arguments={})
    res = executor.execute(call)
    
    assert not res.success
    assert "requires confirmation" in res.error.lower()
    assert res.output is None


def test_executor_restricted_blocked():
    """Verifies RESTRICTED permission level tools are blocked from execution."""
    registry = ToolRegistry()
    registry.register(RestrictedTool())
    executor = ToolExecutor(registry)
    
    call = ToolCall(tool_name="restricted_tool", arguments={})
    res = executor.execute(call)
    
    assert not res.success
    assert "restricted tools" in res.error.lower()
    assert res.output is None


def test_executor_unknown_tool_fails():
    """Verifies calling an unregistered tool name returns a failure result gracefully."""
    registry = ToolRegistry()
    executor = ToolExecutor(registry)
    
    call = ToolCall(tool_name="unknown", arguments={})
    res = executor.execute(call)
    
    assert not res.success
    assert "not registered" in res.error.lower()


def test_executor_invalid_arguments_fails():
    """Verifies invalid parameter types or missing required values fail validation checks."""
    registry = ToolRegistry()
    registry.register(SafeTool())
    executor = ToolExecutor(registry)
    
    # Missing required argument "val"
    call = ToolCall(tool_name="safe_tool", arguments={})
    res = executor.execute(call)
    assert not res.success
    assert "missing required argument" in res.error.lower()

    # Wrong type
    call2 = ToolCall(tool_name="safe_tool", arguments={"val": 123})
    res2 = executor.execute(call2)
    assert not res2.success
    assert "must be of type string" in res2.error.lower()


def test_executor_tool_exception_returns_failed_result():
    """Verifies runtime errors thrown during tool execution do not crash the executor."""
    registry = ToolRegistry()
    registry.register(SafeTool())
    executor = ToolExecutor(registry)
    
    call = ToolCall(tool_name="safe_tool", arguments={"val": "raise"})
    res = executor.execute(call)
    
    assert not res.success
    assert "runtime error during tool execution" in res.error.lower()
    assert res.output is None
