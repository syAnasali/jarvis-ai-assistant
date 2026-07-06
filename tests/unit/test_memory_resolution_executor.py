"""Unit tests for MemoryResolutionExecutor."""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.memory.models import Memory, MemoryCandidate, MemoryType, MemorySource
from app.memory.manager import MemoryManager
from app.memory.resolution import (
    MemoryResolutionAction,
    MemoryResolutionDecision,
    MemoryResolutionExecutor,
)


def create_test_candidate(content: str) -> MemoryCandidate:
    """Helper to create candidate memories."""
    return MemoryCandidate(
        content=content,
        memory_type=MemoryType.PREFERENCE,
        importance=0.8,
        confidence=0.9,
        source=MemorySource.USER,
        evidence="I prefer Python",
        metadata={"foo": "bar"}
    )


def create_test_memory(memory_id: str, content: str) -> Memory:
    """Helper to create active memories."""
    return Memory(
        memory_id=memory_id,
        content=content,
        memory_type=MemoryType.PREFERENCE,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        importance=0.8,
        source=MemorySource.USER,
        metadata={"extraction_method": "llm"}
    )


def test_executor_ignore_action():
    """Verify IGNORE resolution results in no memory manager calls and returns None."""
    mock_manager = MagicMock(spec=MemoryManager)
    executor = MemoryResolutionExecutor(mock_manager)
    cand = create_test_candidate("I prefer Java.")
    decision = MemoryResolutionDecision(
        action=MemoryResolutionAction.IGNORE,
        candidate=cand,
        target_memory_id=None,
        confidence=0.99,
        reason_code="SAME_DURABLE_CLAIM"
    )
    res_id = executor.execute(decision)
    assert res_id is None
    mock_manager.create_memory.assert_not_called()
    mock_manager.update_memory.assert_not_called()
    mock_manager.replace_memory.assert_not_called()


def test_executor_create_action():
    """Verify CREATE resolution instantiates and persists candidate via create_memory."""
    mock_manager = MagicMock(spec=MemoryManager)
    executor = MemoryResolutionExecutor(mock_manager)
    
    cand = create_test_candidate("I prefer Java.")
    decision = MemoryResolutionDecision(
        action=MemoryResolutionAction.CREATE,
        candidate=cand,
        target_memory_id=None,
        confidence=0.95,
        reason_code="NO_RELATED_MEMORY"
    )
    
    stored = create_test_memory("mem_abc", "I prefer Java.")
    mock_manager.create_memory.return_value = stored
    
    res_id = executor.execute(decision)
    assert res_id == "mem_abc"
    mock_manager.create_memory.assert_called_once_with(
        content=cand.content,
        memory_type=cand.memory_type,
        importance=cand.importance,
        source=MemorySource.USER,
        metadata={"extraction_method": "llm", "source": "agent_request", "foo": "bar", "last_resolution_action": "CREATE"}
    )


def test_executor_keep_both_action():
    """Verify KEEP_BOTH resolution instantiates and persists candidate via create_memory."""
    mock_manager = MagicMock(spec=MemoryManager)
    executor = MemoryResolutionExecutor(mock_manager)
    
    cand = create_test_candidate("I prefer Java.")
    decision = MemoryResolutionDecision(
        action=MemoryResolutionAction.KEEP_BOTH,
        candidate=cand,
        target_memory_id="mem_123",
        confidence=0.95,
        reason_code="DISTINCT_SCOPE"
    )
    
    stored = create_test_memory("mem_xyz", "I prefer Java.")
    mock_manager.create_memory.return_value = stored
    
    res_id = executor.execute(decision)
    assert res_id == "mem_xyz"
    mock_manager.create_memory.assert_called_once_with(
        content=cand.content,
        memory_type=cand.memory_type,
        importance=cand.importance,
        source=MemorySource.USER,
        metadata={"extraction_method": "llm", "source": "agent_request", "foo": "bar", "last_resolution_action": "KEEP_BOTH"}
    )


def test_executor_update_action():
    """Verify UPDATE action mutates existing memory via update_memory, preserving created_at and ID."""
    mock_manager = MagicMock(spec=MemoryManager)
    executor = MemoryResolutionExecutor(mock_manager)
    
    cand = create_test_candidate("I prefer JavaScript.")
    original = create_test_memory("mem_123", "I prefer Python.")
    
    mock_manager.get_memory.return_value = original
    updated = create_test_memory("mem_123", "I prefer JavaScript.")
    mock_manager.update_memory.return_value = updated
    
    decision = MemoryResolutionDecision(
        action=MemoryResolutionAction.UPDATE,
        candidate=cand,
        target_memory_id="mem_123",
        confidence=0.96,
        reason_code="UPDATED_PREFERENCE"
    )
    
    res_id = executor.execute(decision)
    assert res_id == "mem_123"
    mock_manager.get_memory.assert_called_once_with("mem_123")
    mock_manager.update_memory.assert_called_once_with(
        memory_id="mem_123",
        content=cand.content,
        memory_type=cand.memory_type,
        importance=cand.importance,
        metadata={"extraction_method": "llm", "last_resolution_action": "UPDATE"}
    )


def test_executor_replace_action():
    """Verify REPLACE action removes old memory and inserts new memory via replace_memory."""
    mock_manager = MagicMock(spec=MemoryManager)
    executor = MemoryResolutionExecutor(mock_manager)
    
    cand = create_test_candidate("I live in Bangalore.")
    original = create_test_memory("mem_456", "I live in Jaipur.")
    
    mock_manager.get_memory.return_value = original
    
    decision = MemoryResolutionDecision(
        action=MemoryResolutionAction.REPLACE,
        candidate=cand,
        target_memory_id="mem_456",
        confidence=0.98,
        reason_code="CHANGED_STATE"
    )
    
    res_id = executor.execute(decision)
    assert res_id is not None
    assert res_id != "mem_456" # must generate a new memory ID
    
    mock_manager.get_memory.assert_called_once_with("mem_456")
    mock_manager.replace_memory.assert_called_once()
    
    # Verify replaced memory fields
    called_args = mock_manager.replace_memory.call_args[0]
    assert called_args[0] == "mem_456"
    new_mem = called_args[1]
    assert new_mem.memory_id == res_id
    assert new_mem.content == cand.content
    assert new_mem.memory_type == cand.memory_type
    assert new_mem.metadata["last_resolution_action"] == "REPLACE"
