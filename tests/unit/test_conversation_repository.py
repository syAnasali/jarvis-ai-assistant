"""Unit tests for SQLiteConversationRepository."""

import pytest
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from app.conversation.models import ConversationSession, SessionStatus
from app.conversation.repository import SQLiteConversationRepository
from app.agent.messages import Message, MessageRole
from app.core.exceptions import (
    ConversationNotFoundError,
    ConversationPersistenceError,
    ConversationValidationError,
    SessionStateError,
)


@pytest.fixture
def temp_db_path(tmp_path) -> Path:
    """Fixture returning a temporary database path."""
    return tmp_path / "test_jarvis.db"


@pytest.fixture
def repository(temp_db_path) -> SQLiteConversationRepository:
    """Fixture returning a SQLiteConversationRepository instance."""
    return SQLiteConversationRepository(database_path=temp_db_path)


def test_schema_initialization(temp_db_path, repository):
    """Verify that tables and indexes are successfully created."""
    assert temp_db_path.exists()
    with repository._connection() as conn:
        # Check sessions table
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='conversation_sessions'")
        assert cursor.fetchone() is not None

        # Check messages table
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='conversation_messages'")
        assert cursor.fetchone() is not None


def test_create_and_retrieve_session(repository):
    """Verify that a session can be persisted and loaded accurately."""
    now = datetime.now(timezone.utc)
    metadata = {"user_pref": "dark_mode"}
    session = ConversationSession(
        session_id="session_abc",
        created_at=now,
        updated_at=now,
        status=SessionStatus.ACTIVE,
        title="Valid Test Session",
        metadata=metadata
    )

    repository.create_session(session)

    retrieved = repository.get_session("session_abc")
    assert retrieved is not None
    assert retrieved.session_id == "session_abc"
    assert abs((retrieved.created_at - now).total_seconds()) < 1.0
    assert abs((retrieved.updated_at - now).total_seconds()) < 1.0
    assert retrieved.status == SessionStatus.ACTIVE
    assert retrieved.title == "Valid Test Session"
    assert retrieved.metadata == metadata


def test_get_session_unknown_returns_none(repository):
    """Verify that retrieving a non-existent session ID returns None."""
    assert repository.get_session("unknown_id") is None


def test_list_sessions_ordered_by_updated_at(repository):
    """Verify list_sessions returns sessions sorted by updated_at descending."""
    now = datetime.now(timezone.utc)
    s1 = ConversationSession("s1", now, now, SessionStatus.ACTIVE, "Session 1", {})
    s2 = ConversationSession("s2", now, now + timedelta(seconds=10), SessionStatus.ACTIVE, "Session 2", {})
    s3 = ConversationSession("s3", now, now + timedelta(seconds=5), SessionStatus.ACTIVE, "Session 3", {})

    repository.create_session(s1)
    repository.create_session(s2)
    repository.create_session(s3)

    sessions = repository.list_sessions()
    assert len(sessions) == 3
    # Ordered by updated_at DESC: s2 (newest), s3, s1 (oldest)
    assert sessions[0].session_id == "s2"
    assert sessions[1].session_id == "s3"
    assert sessions[2].session_id == "s1"


def test_update_session(repository):
    """Verify that an existing session can be updated successfully."""
    now = datetime.now(timezone.utc)
    session = ConversationSession("s1", now, now, SessionStatus.ACTIVE, "Initial Title", {"a": 1})
    repository.create_session(session)

    updated = ConversationSession("s1", now, now + timedelta(seconds=10), SessionStatus.CLOSED, "New Title", {"a": 2})
    repository.update_session(updated)

    retrieved = repository.get_session("s1")
    assert retrieved.title == "New Title"
    assert retrieved.status == SessionStatus.CLOSED
    assert retrieved.metadata == {"a": 2}


def test_update_unknown_session_raises(repository):
    """Verify updating a non-existent session raises ConversationNotFoundError."""
    now = datetime.now(timezone.utc)
    session = ConversationSession("unknown", now, now, SessionStatus.ACTIVE, "Title", {})
    with pytest.raises(ConversationNotFoundError):
        repository.update_session(session)


def test_close_session(repository):
    """Verify close_session marks the session closed and updates updated_at."""
    now = datetime.now(timezone.utc)
    session = ConversationSession("s1", now, now, SessionStatus.ACTIVE, "Active", {})
    repository.create_session(session)

    repository.close_session("s1")

    retrieved = repository.get_session("s1")
    assert retrieved.status == SessionStatus.CLOSED
    assert retrieved.updated_at > now


def test_close_unknown_session_raises(repository):
    """Verify closing an unknown session raises ConversationNotFoundError."""
    with pytest.raises(ConversationNotFoundError):
        repository.close_session("unknown")


def test_add_and_retrieve_messages(repository):
    """Verify messages can be added to session, retrieved in sequence order, and update session.updated_at."""
    now = datetime.now(timezone.utc)
    session = ConversationSession("s1", now, now, SessionStatus.ACTIVE, "Title", {})
    repository.create_session(session)

    m1 = Message("m1", MessageRole.USER, "First query", now, {"a": 1})
    m2 = Message("m2", MessageRole.ASSISTANT, "First response", now + timedelta(seconds=2), {"b": 2})

    repository.add_message("s1", m1)
    repository.add_message("s1", m2)

    messages = repository.get_messages("s1")
    assert len(messages) == 2
    assert messages[0].id == "m1"
    assert messages[0].role == MessageRole.USER
    assert messages[0].content == "First query"
    assert messages[0].metadata == {"a": 1}

    assert messages[1].id == "m2"
    assert messages[1].role == MessageRole.ASSISTANT
    assert messages[1].content == "First response"
    assert messages[1].metadata == {"b": 2}

    # Verify session updated_at was bumped to message timestamp
    sess = repository.get_session("s1")
    assert abs((sess.updated_at - m2.timestamp).total_seconds()) < 1.0

    assert repository.count_messages("s1") == 2


def test_add_message_to_unknown_session_raises(repository):
    """Verify adding a message to a non-existent session ID raises ConversationNotFoundError."""
    m = Message("m1", MessageRole.USER, "Query", datetime.now(timezone.utc), {})
    with pytest.raises(ConversationNotFoundError):
        repository.add_message("unknown", m)


def test_add_message_to_closed_session_raises(repository):
    """Verify adding a message to a closed session raises SessionStateError."""
    now = datetime.now(timezone.utc)
    session = ConversationSession("s1", now, now, SessionStatus.CLOSED, "Closed Session", {})
    repository.create_session(session)

    m = Message("m1", MessageRole.USER, "Query", now, {})
    with pytest.raises(SessionStateError, match="Cannot add message to closed session"):
        repository.add_message("s1", m)


def test_corrupted_session_metadata_raises(temp_db_path, repository):
    """Verify corrupted session metadata JSON causes ConversationPersistenceError."""
    now = datetime.now(timezone.utc)
    session = ConversationSession("s1", now, now, SessionStatus.ACTIVE, "Session 1", {})
    repository.create_session(session)

    # Manually corrupt the metadata column in DB
    with repository._connection() as conn:
        with conn:
            conn.execute("UPDATE conversation_sessions SET metadata = 'invalid_json' WHERE session_id = 's1'")

    with pytest.raises(ConversationPersistenceError, match="Failed to decode session metadata"):
        repository.get_session("s1")


def test_corrupted_message_metadata_raises(temp_db_path, repository):
    """Verify corrupted message metadata JSON causes ConversationPersistenceError."""
    now = datetime.now(timezone.utc)
    session = ConversationSession("s1", now, now, SessionStatus.ACTIVE, "Session 1", {})
    repository.create_session(session)

    m = Message("m1", MessageRole.USER, "Query", now, {})
    repository.add_message("s1", m)

    # Manually corrupt the metadata column in DB
    with repository._connection() as conn:
        with conn:
            conn.execute("UPDATE conversation_messages SET metadata = 'invalid_json' WHERE message_id = 'm1'")

    with pytest.raises(ConversationPersistenceError, match="Failed to decode message metadata"):
        repository.get_messages("s1")


def test_duplicate_message_id_rejected(repository):
    """Verify duplicate message IDs are rejected by unique constraints."""
    now = datetime.now(timezone.utc)
    session = ConversationSession("s1", now, now, SessionStatus.ACTIVE, "Session 1", {})
    repository.create_session(session)

    m1 = Message("dup_id", MessageRole.USER, "Query 1", now, {})
    m2 = Message("dup_id", MessageRole.USER, "Query 2", now, {})

    repository.add_message("s1", m1)
    with pytest.raises(ConversationValidationError, match="Message conflict or duplicate message ID"):
        repository.add_message("s1", m2)


def test_foreign_key_enforcement(repository):
    """Verify SQLite foreign keys are explicitly checked (add message with unknown session ID raises)."""
    m = Message("m1", MessageRole.USER, "Query", datetime.now(timezone.utc), {})
    with pytest.raises(ConversationNotFoundError):
        repository.add_message("unknown_session", m)
