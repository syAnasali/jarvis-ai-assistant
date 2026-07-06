"""Domain models for the conversation session subsystem."""

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any
from app.core.exceptions import ConversationValidationError


class SessionStatus(Enum):
    """Status states of a conversation session."""

    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


@dataclass(frozen=True)
class ConversationSession:
    """Domain model representing a single conversation session.

    Attributes:
        session_id: Centralized unique session identifier.
        created_at: Timezone-aware UTC timestamp.
        updated_at: Timezone-aware UTC timestamp.
        status: The SessionStatus state.
        title: Optional title.
        metadata: Extensible key-value metadata dict.
    """

    session_id: str
    created_at: datetime
    updated_at: datetime
    status: SessionStatus
    title: str | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Validate status
        if not isinstance(self.status, SessionStatus):
            raise ConversationValidationError(f"Invalid session status: {self.status}")

        # Validate timezone-aware datetime objects
        if not isinstance(self.created_at, datetime) or self.created_at.tzinfo is None:
            raise ConversationValidationError("created_at must be a timezone-aware datetime object.")
        if not isinstance(self.updated_at, datetime) or self.updated_at.tzinfo is None:
            raise ConversationValidationError("updated_at must be a timezone-aware datetime object.")

        # Validate metadata
        if not isinstance(self.metadata, dict):
            raise ConversationValidationError("Session metadata must be a dictionary.")

        # Defensive copying of metadata
        object.__setattr__(self, "metadata", deepcopy(self.metadata))
