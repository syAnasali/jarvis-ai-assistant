"""Unit tests for Memory domain models, types, boundaries, and validation constraints."""

import pytest
from datetime import datetime, timezone
from app.core.exceptions import MemoryValidationError
from app.memory.models import Memory, MemorySource, MemoryType


def test_memory_type_values() -> None:
    """Verifies existence and string values of standard memory types."""
    assert MemoryType.FACT.value == "FACT"
    assert MemoryType.PREFERENCE.value == "PREFERENCE"
    assert MemoryType.PROJECT.value == "PROJECT"
    assert MemoryType.CONTEXT.value == "CONTEXT"


def test_memory_source_values() -> None:
    """Verifies existence and string values of standard memory source origins."""
    assert MemorySource.USER.value == "USER"
    assert MemorySource.SYSTEM.value == "SYSTEM"
    assert MemorySource.MANUAL.value == "MANUAL"


def test_valid_memory_construction() -> None:
    """Verifies that a valid Memory object instantiates without validation errors."""
    now = datetime.now(timezone.utc)
    m = Memory(
        memory_id="mem_123",
        content="This is a valid memory statement.",
        memory_type=MemoryType.FACT,
        created_at=now,
        updated_at=now,
        importance=0.5,
        source=MemorySource.USER,
        metadata={"key": "val"}
    )
    assert m.memory_id == "mem_123"
    assert m.content == "This is a valid memory statement."
    assert m.memory_type == MemoryType.FACT
    assert m.created_at == now
    assert m.updated_at == now
    assert m.importance == 0.5
    assert m.source == MemorySource.USER
    assert m.metadata == {"key": "val"}


def test_importance_boundaries() -> None:
    """Verifies boundaries for importance scores (0.0 and 1.0 are valid)."""
    now = datetime.now(timezone.utc)
    # Lower boundary (0.0)
    m_lower = Memory(
        memory_id="mem_low",
        content="Lower bound content",
        memory_type=MemoryType.CONTEXT,
        created_at=now,
        updated_at=now,
        importance=0.0,
        source=MemorySource.MANUAL
    )
    assert m_lower.importance == 0.0

    # Upper boundary (1.0)
    m_upper = Memory(
        memory_id="mem_high",
        content="Upper bound content",
        memory_type=MemoryType.CONTEXT,
        created_at=now,
        updated_at=now,
        importance=1.0,
        source=MemorySource.MANUAL
    )
    assert m_upper.importance == 1.0


def test_invalid_importance_below_range() -> None:
    """Verifies that importance scores below 0.0 raise a MemoryValidationError."""
    now = datetime.now(timezone.utc)
    with pytest.raises(MemoryValidationError) as excinfo:
        Memory(
            memory_id="mem_invalid",
            content="Invalid content",
            memory_type=MemoryType.FACT,
            created_at=now,
            updated_at=now,
            importance=-0.01,
            source=MemorySource.USER
        )
    assert "importance must be between 0.0 and 1.0" in str(excinfo.value)


def test_invalid_importance_above_range() -> None:
    """Verifies that importance scores above 1.0 raise a MemoryValidationError."""
    now = datetime.now(timezone.utc)
    with pytest.raises(MemoryValidationError) as excinfo:
        Memory(
            memory_id="mem_invalid2",
            content="Invalid content",
            memory_type=MemoryType.FACT,
            created_at=now,
            updated_at=now,
            importance=1.01,
            source=MemorySource.USER
        )
    assert "importance must be between 0.0 and 1.0" in str(excinfo.value)


def test_empty_content_rejection() -> None:
    """Verifies that empty content raises a MemoryValidationError."""
    now = datetime.now(timezone.utc)
    with pytest.raises(MemoryValidationError) as excinfo:
        Memory(
            memory_id="mem_empty",
            content="",
            memory_type=MemoryType.FACT,
            created_at=now,
            updated_at=now,
            importance=0.5,
            source=MemorySource.USER
        )
    assert "content must not be empty" in str(excinfo.value)


def test_whitespace_content_rejection() -> None:
    """Verifies that whitespace-only content raises a MemoryValidationError."""
    now = datetime.now(timezone.utc)
    with pytest.raises(MemoryValidationError) as excinfo:
        Memory(
            memory_id="mem_space",
            content="   \n \t  ",
            memory_type=MemoryType.FACT,
            created_at=now,
            updated_at=now,
            importance=0.5,
            source=MemorySource.USER
        )
    assert "content must not be empty" in str(excinfo.value)


def test_invalid_datetime_timezone_naive() -> None:
    """Verifies naive datetime objects raise a MemoryValidationError."""
    naive_now = datetime.now()  # no timezone
    with pytest.raises(MemoryValidationError) as excinfo:
        Memory(
            memory_id="mem_tz",
            content="Valid content",
            memory_type=MemoryType.FACT,
            created_at=naive_now,
            updated_at=datetime.now(timezone.utc),
            importance=0.5,
            source=MemorySource.USER
        )
    assert "must be a timezone-aware datetime" in str(excinfo.value)
