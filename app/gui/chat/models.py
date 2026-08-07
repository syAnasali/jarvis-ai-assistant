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

    def to_dict(self) -> Dict[str, Any]:
        """Serializes message to dictionary."""
        return {
            "message_id": self.message_id,
            "message_type": self.message_type.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "citations": self.citations,
            "attachments": [
                {
                    "filename": getattr(a, "filename", str(a)),
                    "file_path": getattr(a, "file_path", ""),
                    "mime_type": getattr(a, "mime_type", "application/octet-stream"),
                    "file_size_bytes": getattr(a, "file_size_bytes", 0),
                }
                for a in self.attachments
            ],
            "tool_name": self.tool_name,
            "status_tag": self.status_tag,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatMessage":
        """Deserializes dictionary to ChatMessage."""
        atts = [
            AttachmentInfo(
                filename=a.get("filename", ""),
                file_path=a.get("file_path", ""),
                mime_type=a.get("mime_type", "application/octet-stream"),
                file_size_bytes=a.get("file_size_bytes", 0),
            )
            for a in data.get("attachments", [])
        ]
        return cls(
            message_id=data.get("message_id", f"msg_{uuid.uuid4().hex[:10]}"),
            message_type=MessageType(data.get("message_type", "USER")),
            content=data.get("content", ""),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(timezone.utc),
            citations=data.get("citations", []),
            attachments=atts,
            tool_name=data.get("tool_name"),
            status_tag=data.get("status_tag"),
        )


@dataclass
class ConversationSession:
    """Represents an active or persisted chat session thread."""
    title: str = "New Conversation"
    session_id: str = field(default_factory=lambda: f"session_{uuid.uuid4().hex[:8]}")
    messages: List[ChatMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Serializes session to dictionary."""
        return {
            "title": self.title,
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "messages": [m.to_dict() for m in self.messages],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationSession":
        """Deserializes dictionary to ConversationSession."""
        msgs = [ChatMessage.from_dict(m) for m in data.get("messages", [])]
        return cls(
            title=data.get("title", "New Conversation"),
            session_id=data.get("session_id", f"session_{uuid.uuid4().hex[:8]}"),
            messages=msgs,
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(timezone.utc),
        )
