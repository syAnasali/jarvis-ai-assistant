"""Domain models for the memory subsystem."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any
from app.core.exceptions import MemoryValidationError


class MemoryType(Enum):
    """Enumeration of standard memory classifications."""

    FACT = "FACT"
    PREFERENCE = "PREFERENCE"
    PROJECT = "PROJECT"
    CONTEXT = "CONTEXT"


class MemorySource(Enum):
    """Enumeration of standard memory origin sources."""

    USER = "USER"
    SYSTEM = "SYSTEM"
    MANUAL = "MANUAL"


@dataclass(frozen=True)
class Memory:
    """Domain model representing a concise, durable fact or user preference.

    Attributes:
        memory_id: Unique memory identifier.
        content: Concise statement of fact, preference, project, or context.
        memory_type: The semantic category of memory.
        created_at: Timezone-aware timestamp indicating memory creation.
        updated_at: Timezone-aware timestamp indicating last modification.
        importance: Score from 0.0 to 1.0 indicating rank/priority.
        source: The origin source of the memory.
        metadata: Extensible key-value dict storing additional attributes.
    """

    memory_id: str
    content: str
    memory_type: MemoryType
    created_at: datetime
    updated_at: datetime
    importance: float
    source: MemorySource
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Validate content
        if not isinstance(self.content, str):
            raise MemoryValidationError("Memory content must be a string.")
        if not self.content or not self.content.strip():
            raise MemoryValidationError("Memory content must not be empty or whitespace-only.")

        # Validate importance
        # We need to handle float type and range checks
        try:
            val = float(self.importance)
        except (ValueError, TypeError) as e:
            raise MemoryValidationError(f"Memory importance must be a numeric score, got {self.importance}") from e

        if val < 0.0 or val > 1.0:
            raise MemoryValidationError(f"Memory importance must be between 0.0 and 1.0, got {self.importance}")

        # Validate memory_type
        if not isinstance(self.memory_type, MemoryType):
            raise MemoryValidationError(f"Invalid memory type: {self.memory_type}")

        # Validate source
        if not isinstance(self.source, MemorySource):
            raise MemoryValidationError(f"Invalid memory source: {self.source}")

        # Validate timezone-aware datetime objects
        if not isinstance(self.created_at, datetime) or self.created_at.tzinfo is None:
            raise MemoryValidationError("created_at must be a timezone-aware datetime object.")
        if not isinstance(self.updated_at, datetime) or self.updated_at.tzinfo is None:
            raise MemoryValidationError("updated_at must be a timezone-aware datetime object.")

        # Validate metadata
        if not isinstance(self.metadata, dict):
            raise MemoryValidationError("Memory metadata must be a dictionary.")
