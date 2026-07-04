"""Intent models representing parsed user goals."""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any


class IntentType(Enum):
    """Enumeration of recognized user prompt intents."""

    CHAT = "chat"
    TOOL = "tool"
    MEMORY_READ = "memory_read"
    MEMORY_WRITE = "memory_write"
    SYSTEM = "system"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Intent:
    """Represents a classified user intent.

    Attributes:
        intent_type: The classified type of the intent.
        confidence: The confidence score (0.0 to 1.0) of the classification.
        metadata: Additional unstructured metadata.
    """

    intent_type: IntentType
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
