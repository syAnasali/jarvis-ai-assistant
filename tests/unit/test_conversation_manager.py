"""Unit tests for ConversationManager."""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock
from app.conversation.models import ConversationSession, SessionStatus
from app.conversation.interfaces import ConversationRepository
from app.conversation.manager import ConversationManager
from app.agent.messages import Message, MessageRole
from app.agent.conversation import Conversation
from app.core.exceptions import ConversationNotFoundError, SessionStateError, ConversationPersistenceError


def test_create_session_generates_id_and_timestamps():
    """Verify that create_session properly populates session metadata and persists it."""
    mock_repo = MagicMock(spec=ConversationRepository)
    manager = ConversationManager(mock_repo)

    session = manager.create_session(title="New Session", metadata={"user": "Anas"})

    assert session.session_id.startswith("session_")
    assert session.title == "New Session"
    assert session.metadata == {"user": "Anas"}
    assert session.status == SessionStatus.ACTIVE
    assert session.created_at.tzinfo == timezone.utc
    assert session.updated_at.tzinfo == timezone.utc

    mock_repo.create_session.assert_called_once_with(session)


def test_load_session_delegates_to_repository():
    """Verify load_session retrieves the session or raises if missing."""
    mock_repo = MagicMock(spec=ConversationRepository)
    manager = ConversationManager(mock_repo)

    dummy = ConversationSession("s123", datetime.now(timezone.utc), datetime.now(timezone.utc), SessionStatus.ACTIVE, "Session", {})
    mock_repo.get_session.return_value = dummy

    # Found
    res = manager.load_session("s123")
    assert res == dummy
    mock_repo.get_session.assert_called_once_with("s123")

    # Not found
    mock_repo.get_session.return_value = None
    with pytest.raises(ConversationNotFoundError, match="session s123 not found"):
        manager.load_session("s123")


def test_list_sessions_delegation():
    """Verify list_sessions retrieves from repository."""
    mock_repo = MagicMock(spec=ConversationRepository)
    manager = ConversationManager(mock_repo)
    manager.list_sessions()
    mock_repo.list_sessions.assert_called_once()


def test_close_session_delegation():
    """Verify close_session retrieves from repository."""
    mock_repo = MagicMock(spec=ConversationRepository)
    manager = ConversationManager(mock_repo)
    manager.close_session("s123")
    mock_repo.close_session.assert_called_once_with("s123")


def test_add_message_delegation():
    """Verify add_message persists via repository."""
    mock_repo = MagicMock(spec=ConversationRepository)
    manager = ConversationManager(mock_repo)

    msg = Message("m1", MessageRole.USER, "Hello", datetime.now(timezone.utc), {})
    manager.add_message("s123", msg)

    mock_repo.add_message.assert_called_once_with("s123", msg)


def test_hydrate_conversation_preserves_id_roles_ordering():
    """Verify hydration of Conversation model from persistent messages log."""
    mock_repo = MagicMock(spec=ConversationRepository)
    manager = ConversationManager(mock_repo)

    m1 = Message("msg_1", MessageRole.USER, "First query", datetime.now(timezone.utc), {"a": 1})
    m2 = Message("msg_2", MessageRole.ASSISTANT, "First answer", datetime.now(timezone.utc), {"b": 2})

    mock_repo.get_messages.return_value = [m1, m2]

    conversation = Conversation()
    messages = manager.get_messages("s123")
    conversation.load_history(messages)

    history = conversation.get_history()
    assert len(history) == 2
    assert history[0].id == "msg_1"
    assert history[0].role == MessageRole.USER
    assert history[0].content == "First query"
    assert history[0].metadata == {"a": 1}

    assert history[1].id == "msg_2"
    assert history[1].role == MessageRole.ASSISTANT
    assert history[1].content == "First answer"
    assert history[1].metadata == {"b": 2}


def test_repository_exceptions_propagate():
    """Verify repository exceptions bubble up through manager wrapper."""
    mock_repo = MagicMock(spec=ConversationRepository)
    manager = ConversationManager(mock_repo)
    mock_repo.create_session.side_effect = ConversationPersistenceError("Database failure")

    with pytest.raises(ConversationPersistenceError, match="Database failure"):
        manager.create_session()
