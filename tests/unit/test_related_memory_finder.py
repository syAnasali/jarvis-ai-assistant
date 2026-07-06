"""Unit tests for RelatedMemoryFinder."""

import pytest
from datetime import datetime, timezone

from app.memory.models import Memory, MemoryCandidate, MemoryType, MemorySource
from app.memory.related import RelatedMemoryFinder


def create_test_candidate(content: str, memory_type: MemoryType = MemoryType.PREFERENCE) -> MemoryCandidate:
    """Helper to create candidate memories."""
    return MemoryCandidate(
        content=content,
        memory_type=memory_type,
        importance=0.8,
        confidence=0.9,
        source=MemorySource.USER,
        evidence="Some statement",
        metadata={}
    )


def create_test_memory(memory_id: str, content: str, memory_type: MemoryType, importance: float = 0.8) -> Memory:
    """Helper to create active memories."""
    return Memory(
        memory_id=memory_id,
        content=content,
        memory_type=memory_type,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        importance=importance,
        source=MemorySource.USER,
        metadata={}
    )


def test_finder_empty_database():
    """Verify finder returns empty list when no database memories exist."""
    finder = RelatedMemoryFinder()
    cand = create_test_candidate("I prefer Python.")
    related = finder.find_related(cand, [])
    assert related == []


def test_finder_exact_matching_preference():
    """Verify exact or highly similar preferences are found as related."""
    finder = RelatedMemoryFinder()
    cand = create_test_candidate("The user prefers Python.")
    
    mem1 = create_test_memory("mem_1", "The user prefers Python.", MemoryType.PREFERENCE)
    mem2 = create_test_memory("mem_2", "The user lives in Jaipur.", MemoryType.FACT)
    
    related = finder.find_related(cand, [mem1, mem2])
    assert len(related) == 1
    assert related[0].memory_id == "mem_1"


def test_finder_changed_value_remains_related():
    """Verify a change in preference value (e.g. Python -> JavaScript) is identified as related."""
    finder = RelatedMemoryFinder()
    # Candidate prefers JavaScript, existing prefers Python. They share "user prefers personal projects".
    cand = create_test_candidate("The user prefers JavaScript for personal projects.")
    
    mem1 = create_test_memory("mem_1", "The user prefers Python for personal projects.", MemoryType.PREFERENCE)
    mem2 = create_test_memory("mem_2", "The user is building AcadConnect.", MemoryType.PROJECT)
    
    related = finder.find_related(cand, [mem1, mem2])
    assert len(related) >= 1
    assert related[0].memory_id == "mem_1"


def test_finder_unrelated_preference_and_project():
    """Verify unrelated projects and preferences do not overlap."""
    finder = RelatedMemoryFinder()
    cand = create_test_candidate("The user prefers Python for AI projects.", MemoryType.PREFERENCE)
    
    # mem1 is location fact, no meaningful overlap
    mem1 = create_test_memory("mem_1", "The user lives in Bangalore.", MemoryType.FACT)
    
    related = finder.find_related(cand, [mem1])
    # Since they only share low-information "user" which is filtered out, they should have 0 overlap.
    assert len(related) == 0


def test_finder_bounded_results_limit():
    """Verify the finder bounds the returned list size and orders deterministically."""
    # Centralized limit of 3
    finder = RelatedMemoryFinder(limit=3)
    cand = create_test_candidate("The user prefers Python for projects.")
    
    m1 = create_test_memory("m1", "The user prefers Python for projects.", MemoryType.PREFERENCE, importance=0.9)
    m2 = create_test_memory("m2", "The user prefers Python for personal tasks.", MemoryType.PREFERENCE, importance=0.8)
    m3 = create_test_memory("m3", "The user likes coding in Python.", MemoryType.PREFERENCE, importance=0.7)
    m4 = create_test_memory("m4", "The user does projects.", MemoryType.PROJECT, importance=0.6)
    m5 = create_test_memory("m5", "The user builds software.", MemoryType.PROJECT, importance=0.5)
    
    related = finder.find_related(cand, [m5, m4, m3, m2, m1])
    
    # Bounded to 3
    assert len(related) == 3
    # Deterministically ordered (m1 is exact match, m2 is next closest, m3 is next)
    assert [m.memory_id for m in related] == ["m1", "m2", "m3"]


def test_finder_input_not_mutated():
    """Verify candidate and database list are not mutated by the finder."""
    finder = RelatedMemoryFinder()
    cand = create_test_candidate("The user prefers Python.")
    mem_list = [
        create_test_memory("m1", "The user prefers Python.", MemoryType.PREFERENCE),
        create_test_memory("m2", "The user lives in Jaipur.", MemoryType.FACT)
    ]
    
    mem_list_copy = list(mem_list)
    finder.find_related(cand, mem_list)
    
    assert mem_list == mem_list_copy
    assert cand.content == "The user prefers Python."
