"""Unit tests for SQLiteMemoryRepository operations and persistence constraints."""

import tempfile
import sqlite3
import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from app.core.exceptions import (
    MemoryNotFoundError,
    MemoryValidationError,
    MemoryPersistenceError,
)
from app.memory.models import Memory, MemorySource, MemoryType
from app.memory.repository import SQLiteMemoryRepository


@pytest.fixture
def temp_db_path() -> Path:
    """Fixture providing a temporary database file path and cleaning up after test."""
    temp_dir = tempfile.TemporaryDirectory()
    db_file = Path(temp_dir.name) / "test_memories.db"
    yield db_file
    try:
        temp_dir.cleanup()
    except Exception:
        pass


def test_repository_initialization(temp_db_path: Path) -> None:
    """Verifies that the repository creates the required memories table on start."""
    repo = SQLiteMemoryRepository(database_path=temp_db_path)
    assert temp_db_path.exists()

    # Query sqlite_master to verify memories table exists
    conn = sqlite3.connect(str(temp_db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='memories';")
    row = cursor.fetchone()
    conn.close()
    assert row is not None
    assert row[0] == "memories"


def test_repository_add_and_get(temp_db_path: Path) -> None:
    """Verifies persisting and retrieving a memory preserves all attributes."""
    repo = SQLiteMemoryRepository(database_path=temp_db_path)
    now = datetime.now(timezone.utc)
    m = Memory(
        memory_id="mem_abc",
        content="Testing database insert.",
        memory_type=MemoryType.FACT,
        created_at=now,
        updated_at=now,
        importance=0.75,
        source=MemorySource.MANUAL,
        metadata={"project": "Jarvis", "active": True}
    )

    repo.add(m)
    retrieved = repo.get("mem_abc")

    assert retrieved is not None
    assert retrieved.memory_id == "mem_abc"
    assert retrieved.content == "Testing database insert."
    assert retrieved.memory_type == MemoryType.FACT
    assert retrieved.importance == 0.75
    assert retrieved.source == MemorySource.MANUAL
    assert retrieved.metadata == {"project": "Jarvis", "active": True}

    # Verify datetimes are reconstructed as timezone-aware UTC datetimes
    assert retrieved.created_at.tzinfo is not None
    assert retrieved.updated_at.tzinfo is not None
    # Compare with a small delta since ISO serialization might lose subsecond precision or type info
    assert abs((retrieved.created_at - now).total_seconds()) < 1.0


def test_repository_list_all_and_count(temp_db_path: Path) -> None:
    """Verifies repository listing and count reporting."""
    repo = SQLiteMemoryRepository(database_path=temp_db_path)
    assert repo.count() == 0
    assert len(repo.list_all()) == 0

    now = datetime.now(timezone.utc)
    m1 = Memory(
        memory_id="mem_1",
        content="First memory statement.",
        memory_type=MemoryType.PREFERENCE,
        created_at=now,
        updated_at=now,
        importance=0.5,
        source=MemorySource.USER
    )
    m2 = Memory(
        memory_id="mem_2",
        content="Second memory statement.",
        memory_type=MemoryType.PROJECT,
        created_at=now,
        updated_at=now,
        importance=0.9,
        source=MemorySource.SYSTEM
    )

    repo.add(m1)
    assert repo.count() == 1

    repo.add(m2)
    assert repo.count() == 2

    all_memories = repo.list_all()
    assert len(all_memories) == 2
    ids = {m.memory_id for m in all_memories}
    assert ids == {"mem_1", "mem_2"}


def test_repository_update_success(temp_db_path: Path) -> None:
    """Verifies that updating a memory correctly overrides matching database attributes."""
    repo = SQLiteMemoryRepository(database_path=temp_db_path)
    now = datetime.now(timezone.utc)
    m = Memory(
        memory_id="mem_upd",
        content="Original memory content.",
        memory_type=MemoryType.CONTEXT,
        created_at=now,
        updated_at=now,
        importance=0.4,
        source=MemorySource.MANUAL,
        metadata={"tags": ["old"]}
    )
    repo.add(m)

    updated_time = now + timedelta(minutes=5)
    updated_m = Memory(
        memory_id="mem_upd",
        content="Fully updated memory content.",
        memory_type=MemoryType.PREFERENCE,
        created_at=now,  # preserved
        updated_at=updated_time,
        importance=0.85,
        source=MemorySource.MANUAL,
        metadata={"tags": ["new", "updated"]}
    )

    repo.update(updated_m)
    retrieved = repo.get("mem_upd")

    assert retrieved is not None
    assert retrieved.content == "Fully updated memory content."
    assert retrieved.memory_type == MemoryType.PREFERENCE
    assert retrieved.importance == 0.85
    assert retrieved.metadata == {"tags": ["new", "updated"]}
    assert abs((retrieved.updated_at - updated_time).total_seconds()) < 1.0


def test_repository_update_unknown_raises(temp_db_path: Path) -> None:
    """Verifies updating an unknown memory ID raises MemoryNotFoundError."""
    repo = SQLiteMemoryRepository(database_path=temp_db_path)
    now = datetime.now(timezone.utc)
    m = Memory(
        memory_id="mem_missing",
        content="Content to update",
        memory_type=MemoryType.FACT,
        created_at=now,
        updated_at=now,
        importance=0.5,
        source=MemorySource.USER
    )

    with pytest.raises(MemoryNotFoundError):
        repo.update(m)


def test_repository_delete_success(temp_db_path: Path) -> None:
    """Verifies deleting a memory ID removes it from database."""
    repo = SQLiteMemoryRepository(database_path=temp_db_path)
    now = datetime.now(timezone.utc)
    m = Memory(
        memory_id="mem_del",
        content="Delete target.",
        memory_type=MemoryType.FACT,
        created_at=now,
        updated_at=now,
        importance=0.5,
        source=MemorySource.USER
    )
    repo.add(m)
    assert repo.count() == 1

    repo.delete("mem_del")
    assert repo.count() == 0
    assert repo.get("mem_del") is None


def test_repository_delete_unknown_raises(temp_db_path: Path) -> None:
    """Verifies deleting an unknown memory ID raises MemoryNotFoundError."""
    repo = SQLiteMemoryRepository(database_path=temp_db_path)
    with pytest.raises(MemoryNotFoundError):
        repo.delete("mem_missing")


def test_database_constraints_importance(temp_db_path: Path) -> None:
    """Verifies that SQLite database-level constraints reject invalid values on add/update."""
    repo = SQLiteMemoryRepository(database_path=temp_db_path)
    now = datetime.now(timezone.utc)

    # We bypass domain model validations by executing SQL directly to verify database constraints
    # This verifies the database schema itself has table-level validation constraints
    conn = sqlite3.connect(str(temp_db_path))
    
    # 1. Invalid importance (> 1.0)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO memories (
                memory_id, content, memory_type, created_at, updated_at, importance, source, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("m1", "Content", "FACT", now.isoformat(), now.isoformat(), 1.05, "USER", "{}")
        )

    # 2. Invalid empty content
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO memories (
                memory_id, content, memory_type, created_at, updated_at, importance, source, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("m2", "   ", "FACT", now.isoformat(), now.isoformat(), 0.5, "USER", "{}")
        )
    conn.close()


def test_corrupted_metadata_raises_persistence_error(temp_db_path: Path) -> None:
    """Verifies that invalid metadata JSON in DB raises MemoryPersistenceError on retrieval."""
    repo = SQLiteMemoryRepository(database_path=temp_db_path)
    now = datetime.now(timezone.utc)

    # Directly insert corrupted JSON
    conn = sqlite3.connect(str(temp_db_path))
    conn.execute(
        """
        INSERT INTO memories (
            memory_id, content, memory_type, created_at, updated_at, importance, source, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("m_corrupted", "Content", "FACT", now.isoformat(), now.isoformat(), 0.5, "USER", "{invalid_json")
    )
    conn.commit()
    conn.close()

    with pytest.raises(MemoryPersistenceError) as excinfo:
        repo.get("m_corrupted")
    assert "Failed to decode memory metadata JSON" in str(excinfo.value)
