"""Domain models for the Action Approval Subsystem."""

import copy
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from app.tools.models import ToolPermission


class PendingActionStatus(Enum):
    """Lifecycle statuses of a pending confirmation action."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    EXECUTED = "executed"
    FAILED = "failed"


@dataclass(frozen=True)
class PendingAction:
    """Immutable record of an action awaiting user approval."""

    action_id: str
    tool_name: str
    arguments: Dict[str, Any]
    permission_level: ToolPermission
    status: PendingActionStatus
    created_at: datetime
    expires_at: datetime
    reason: str
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Enforces timezone awareness and defensive deep copies of arguments and metadata."""
        if self.created_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValueError("All datetime fields must be timezone-aware.")
            
        # Freeze copies of mutable arguments and metadata
        object.__setattr__(self, "arguments", copy.deepcopy(self.arguments))
        object.__setattr__(self, "metadata", copy.deepcopy(self.metadata))
