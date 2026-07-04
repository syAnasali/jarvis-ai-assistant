"""Data models for the Tool Execution subsystem."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict


class ToolPermission(Enum):
    """Enumeration of tool execution safety permission levels."""

    SAFE = "safe"
    CONFIRMATION = "confirmation"
    RESTRICTED = "restricted"


@dataclass(frozen=True)
class ToolResult:
    """Immutable representation of a tool execution attempt.

    Attributes:
        tool_name: The name of the executed tool.
        success: Whether the execution succeeded.
        output: The output value returned by the tool, or None if failed.
        error: Diagnostic error message in case of failure, or None if successful.
        metadata: Unstructured execution metadata (e.g. timestamps, timing).
    """

    tool_name: str
    success: bool
    output: Any | None = None
    error: str | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)
