"""Domain models for Chat Interface, message types, and attachments."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class MessageType(Enum):
    """Enumeration of chat message types."""
    USER = "USER"
    ASSISTANT = "ASSISTANT"
    SYSTEM = "SYSTEM"
    TOOL = "TOOL"
    PLANNER = "PLANNER"
    APPROVAL = "APPROVAL"
    ERROR = "ERROR"


@dataclass(frozen=True)
class AttachmentInfo:
    """Represents an attached image or document file."""
    filename: str
    file_path: str
    mime_type: str = "application/octet-stream"
    file_size_bytes: int = 0


@dataclass
class ChatMessage:
    """Represents an individual chat message in the conversation thread."""
    message_type: MessageType
    content: str
    message_id: str = field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:10]}")
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    citations: List[Dict[str, Any]] = field(default_factory=list)
    attachments: List[AttachmentInfo] = field(default_factory=list)
    tool_name: Optional[str] = None
    status_tag: Optional[str] = None


@dataclass
class ConversationSession:
    """Represents an active or persisted chat session thread."""
    title: str = "New Conversation"
    session_id: str = field(default_factory=lambda: f"session_{uuid.uuid4().hex[:8]}")
    messages: List[ChatMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
