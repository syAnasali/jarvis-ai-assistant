"""Message models for the Agent Engine."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any


class MessageRole(Enum):
    """Enumeration of potential roles for a conversation message."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(frozen=True)
class Message:
    """Immutable representation of a message in a conversation.

    Attributes:
        id: Unique identifier for the message.
        role: The role of the entity that sent the message.
        content: The text content of the message.
        timestamp: Time when the message was created.
        metadata: Additional unstructured data associated with the message.
    """

    id: str
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
