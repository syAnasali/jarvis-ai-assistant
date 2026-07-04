"""Unit tests for ToolRegistry."""

import pytest
from app.tools.base import BaseTool
from app.tools.models import ToolPermission
from app.tools.registry import ToolRegistry
from app.core.exceptions import ToolExecutionError


class DummyTool(BaseTool):
    """Mock BaseTool for testing registry operations."""

    @property
    def name(self) -> str:
        return "dummy"

    @property
    def description(self) -> str:
        return "A dummy test tool"

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.SAFE

    def get_schema(self) -> dict:
        return {"name": self.name}

    def execute(self, **kwargs) -> str:
        return "ok"


def test_registry_register_and_retrieve():
    """Verifies tools can be registered, detected, and fetched from registry."""
    registry = ToolRegistry()
    tool = DummyTool()
    
    assert not registry.has("dummy")
    registry.register(tool)
    
    assert registry.has("dummy")
    assert registry.get("dummy") is tool
    assert "dummy" in registry.list_tools()


def test_registry_duplicate_fails():
    """Verifies duplicate tool names trigger registry errors."""
    registry = ToolRegistry()
    tool = DummyTool()
    registry.register(tool)
    
    with pytest.raises(ToolExecutionError):
        registry.register(tool)


def test_registry_unknown_retrieval_fails():
    """Verifies fetching unregistered tool names throws errors."""
    registry = ToolRegistry()
    with pytest.raises(ToolExecutionError):
        registry.get("unknown")


def test_registry_remove():
    """Verifies tools can be removed from registry."""
    registry = ToolRegistry()
    tool = DummyTool()
    registry.register(tool)
    
    registry.remove("dummy")
    assert not registry.has("dummy")


def test_registry_unknown_remove_fails():
    """Verifies removing unregistered tool names throws errors."""
    registry = ToolRegistry()
    with pytest.raises(ToolExecutionError):
        registry.remove("unknown")


def test_registry_get_schemas():
    """Verifies registry aggregates all tool schemas correctly."""
    registry = ToolRegistry()
    tool = DummyTool()
    registry.register(tool)
    
    schemas = registry.get_schemas()
    assert len(schemas) == 1
    assert schemas[0] == {"name": "dummy"}
