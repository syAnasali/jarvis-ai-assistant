"""Unit tests for MemoryManager using a fake memory repository double."""

import pytest
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from app.core.exceptions import MemoryNotFoundError, MemoryValidationError
from app.memory.interfaces import MemoryRepository
from app.memory.models import Memory, MemorySource, MemoryType
from app.memory.manager import MemoryManager


class FakeMemoryRepository(MemoryRepository):
    """In-memory fake repository test double."""

    def __init__(self) -> None:
        self.db: Dict[str, Memory] = {}

    def add(self, memory: Memory) -> None:
        self.db[memory.memory_id] = memory

    def get(self, memory_id: str) -> Memory | None:
        return self.db.get(memory_id)

    def list_all(self) -> List[Memory]:
        return list(self.db.values())

    def update(self, memory: Memory) -> None:
        if memory.memory_id not in self.db:
            raise MemoryNotFoundError(f"Memory with ID {memory.memory_id} not found.")
        self.db[memory.memory_id] = memory

    def delete(self, memory_id: str) -> None:
        if memory_id not in self.db:
            raise MemoryNotFoundError(f"Memory with ID {memory_id} not found.")
        del self.db[memory_id]

    def count(self) -> int:
        return len(self.db)


def test_manager_memory_creation() -> None:
    """Verifies that MemoryManager creates, stores, and validates memory."""
    repo = FakeMemoryRepository()
    manager = MemoryManager(repo)

    metadata = {"active_proj": True}
    m = manager.create_memory(
        content="Testing manager creation.",
        memory_type=MemoryType.FACT,
        importance=0.8,
        source=MemorySource.MANUAL,
        metadata=metadata
    )

    # Check returned memory domain object values
    assert m is not None
    assert m.memory_id.startswith("mem_")
    assert len(m.memory_id) > 4
    assert m.content == "Testing manager creation."
    assert m.memory_type == MemoryType.FACT
    assert m.importance == 0.8
    assert m.source == MemorySource.MANUAL
    assert m.metadata == {"active_proj": True}

    # Verify timezone-aware UTC timestamps
    assert m.created_at.tzinfo is not None
    assert m.updated_at.tzinfo is not None
    assert m.created_at == m.updated_at
    assert abs((m.created_at - datetime.now(timezone.utc)).total_seconds()) < 5.0

    # Verify delegation and storage in repo
    assert repo.count() == 1
    stored = repo.get(m.memory_id)
    assert stored == m


def test_manager_metadata_not_mutated() -> None:
    """Verifies caller-provided metadata dictionary is not mutated inside manager."""
    repo = FakeMemoryRepository()
    manager = MemoryManager(repo)

    caller_metadata = {"tags": ["original"]}
    m = manager.create_memory(
        content="Do not mutate metadata",
        memory_type=MemoryType.CONTEXT,
        importance=0.5,
        source=MemorySource.USER,
        metadata=caller_metadata
    )

    # Mutate the memory metadata inside domain class or modify caller dictionary
    caller_metadata["tags"].append("mutated")
    assert m.metadata == {"tags": ["original"]}  # should remain original


def test_manager_retrieval_and_list() -> None:
    """Verifies getting and listing delegation from manager."""
    repo = FakeMemoryRepository()
    manager = MemoryManager(repo)

    m1 = manager.create_memory("M1", MemoryType.FACT, 0.5, MemorySource.USER)
    m2 = manager.create_memory("M2", MemoryType.PREFERENCE, 0.6, MemorySource.USER)

    assert manager.count_memories() == 2
    assert manager.get_memory(m1.memory_id) == m1
    assert manager.get_memory("nonexistent") is None

    all_mem = manager.list_memories()
    assert len(all_mem) == 2
    assert {m.memory_id for m in all_mem} == {m1.memory_id, m2.memory_id}


def test_manager_update_success() -> None:
    """Verifies manager update correctly creates new Memory object and updates repository."""
    repo = FakeMemoryRepository()
    manager = MemoryManager(repo)

    m = manager.create_memory(
        content="Original statement.",
        memory_type=MemoryType.FACT,
        importance=0.5,
        source=MemorySource.MANUAL,
        metadata={"a": 1}
    )
    original_id = m.memory_id
    original_created_at = m.created_at
    original_updated_at = m.updated_at

    # Wait briefly or simulate time passing for updated_at check
    # We'll construct a mock timedelta check or verify timestamp change
    updated = manager.update_memory(
        memory_id=original_id,
        content="Updated statement.",
        importance=0.9,
        metadata={"a": 2}
    )

    assert updated.memory_id == original_id
    assert updated.content == "Updated statement."
    assert updated.importance == 0.9
    assert updated.metadata == {"a": 2}
    assert updated.created_at == original_created_at  # preserved
    assert updated.updated_at > original_updated_at  # chronologically valid/newer
    assert updated.source == MemorySource.MANUAL  # preserved

    # Verify repository storage was updated
    stored = repo.get(original_id)
    assert stored == updated


def test_manager_update_unknown_raises() -> None:
    """Verifies updating an unknown memory raises MemoryNotFoundError."""
    repo = FakeMemoryRepository()
    manager = MemoryManager(repo)

    with pytest.raises(MemoryNotFoundError):
        manager.update_memory("missing_id", content="Updated")


def test_manager_delete_delegation() -> None:
    """Verifies deleting memory removes it from repository."""
    repo = FakeMemoryRepository()
    manager = MemoryManager(repo)

    m = manager.create_memory("To delete", MemoryType.FACT, 0.5, MemorySource.USER)
    assert repo.count() == 1

    manager.delete_memory(m.memory_id)
    assert repo.count() == 0
    assert manager.get_memory(m.memory_id) is None


def test_manager_delete_unknown_raises() -> None:
    """Verifies deleting unknown memory raises MemoryNotFoundError."""
    repo = FakeMemoryRepository()
    manager = MemoryManager(repo)

    with pytest.raises(MemoryNotFoundError):
        manager.delete_memory("missing_id")


def test_manager_validation_failures() -> None:
    """Verifies memory manager creation rejects invalid parameter formats."""
    repo = FakeMemoryRepository()
    manager = MemoryManager(repo)

    # Empty content
    with pytest.raises(MemoryValidationError):
        manager.create_memory("", MemoryType.FACT, 0.5, MemorySource.USER)

    # Importance below 0.0
    with pytest.raises(MemoryValidationError):
        manager.create_memory("Valid", MemoryType.FACT, -0.1, MemorySource.USER)

    # Importance above 1.0
    with pytest.raises(MemoryValidationError):
        manager.create_memory("Valid", MemoryType.FACT, 1.05, MemorySource.USER)

    # Invalid metadata type
    with pytest.raises(MemoryValidationError):
        manager.create_memory("Valid", MemoryType.FACT, 0.5, MemorySource.USER, metadata="not_a_dict")  # type: ignore
