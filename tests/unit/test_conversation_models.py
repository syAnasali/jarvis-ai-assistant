"""Unit tests for conversation session and status domain models."""

import pytest
from datetime import datetime, timezone
from app.conversation.models import ConversationSession, SessionStatus
from app.core.exceptions import ConversationValidationError


def test_valid_session_creation():
    """Verify that a valid ConversationSession is successfully constructed."""
    now = datetime.now(timezone.utc)
    metadata = {"key": "value"}
    session = ConversationSession(
        session_id="session_123",
        created_at=now,
        updated_at=now,
        status=SessionStatus.ACTIVE,
        title="Valid Session",
        metadata=metadata
    )
    assert session.session_id == "session_123"
    assert session.created_at == now
    assert session.updated_at == now
    assert session.status == SessionStatus.ACTIVE
    assert session.title == "Valid Session"
    assert session.metadata == metadata


def test_naive_datetime_rejection():
    """Verify that naive datetime objects cause validation failure."""
    now_naive = datetime.now()
    now_aware = datetime.now(timezone.utc)

    # Naive created_at
    with pytest.raises(ConversationValidationError, match="created_at must be a timezone-aware datetime"):
        ConversationSession(
            session_id="session_123",
            created_at=now_naive,
            updated_at=now_aware,
            status=SessionStatus.ACTIVE,
            metadata={}
        )

    # Naive updated_at
    with pytest.raises(ConversationValidationError, match="updated_at must be a timezone-aware datetime"):
        ConversationSession(
            session_id="session_123",
            created_at=now_aware,
            updated_at=now_naive,
            status=SessionStatus.ACTIVE,
            metadata={}
        )


def test_metadata_defensive_handling():
    """Verify that metadata is defensively deepcopied to prevent external mutation."""
    now = datetime.now(timezone.utc)
    metadata = {"tags": ["test", "diagnostic"], "nested": {"param": 42}}
    session = ConversationSession(
        session_id="session_123",
        created_at=now,
        updated_at=now,
        status=SessionStatus.ACTIVE,
        metadata=metadata
    )

    # Mutate external dictionary
    metadata["tags"].append("mutated")
    metadata["nested"]["param"] = 999

    # Assert that session's metadata remained unchanged
    assert session.metadata["tags"] == ["test", "diagnostic"]
    assert session.metadata["nested"]["param"] == 42


def test_invalid_status_type():
    """Verify that invalid SessionStatus types are rejected."""
    now = datetime.now(timezone.utc)
    with pytest.raises(ConversationValidationError, match="Invalid session status"):
        ConversationSession(
            session_id="session_123",
            created_at=now,
            updated_at=now,
            status="ACTIVE",  # String instead of SessionStatus Enum
            metadata={}
        )
