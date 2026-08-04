"""Unit tests for Chat domain models."""

import pytest
from app.gui.chat.models import (
    MessageType,
    AttachmentInfo,
    ChatMessage,
    ConversationSession,
)


def test_chat_models():
    att = AttachmentInfo(filename="doc.pdf", file_path="/tmp/doc.pdf", file_size_bytes=1024)
    msg = ChatMessage(message_type=MessageType.USER, content="Hello", attachments=[att])

    assert msg.message_type == MessageType.USER
    assert msg.content == "Hello"
    assert len(msg.attachments) == 1
    assert msg.attachments[0].filename == "doc.pdf"

    session = ConversationSession(title="Test Session")
    session.messages.append(msg)
    assert len(session.messages) == 1
