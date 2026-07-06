"""Unit tests for the memory retrieval system."""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.core.exceptions import MemoryValidationError
from app.memory.models import Memory, MemoryType, MemorySource
from app.memory.interfaces import MemoryRepository
from app.memory.retrieval import (
    LexicalMemoryRetriever,
    normalize_text,
    LEXICAL_THRESHOLD
)


def create_test_memory(memory_id: str, content: str, importance: float = 0.5) -> Memory:
    """Helper to create dummy memory objects."""
    return Memory(
        memory_id=memory_id,
        content=content,
        memory_type=MemoryType.FACT,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        importance=importance,
        source=MemorySource.MANUAL,
        metadata={}
    )


def test_text_normalization():
    """Verify text is normalized correctly."""
    assert normalize_text("Hello WORLD!") == ["hello", "world"]
    assert normalize_text("Python, Java; C++.") == ["python", "java", "c"]
    assert normalize_text("") == []
    assert normalize_text(None) == []


def test_punctuation_handling():
    """Verify punctuation characters are ignored/cleaned."""
    assert normalize_text("name? or preferences...!") == ["name", "or", "preferences"]


def test_case_normalization():
    """Verify lowercasing is applied."""
    assert normalize_text("ANAS name") == ["anas", "name"]


def test_stop_word_filtering():
    """Verify basic English stop-words are removed."""
    # stop-words: the, a, an, is, are, of, to, for, and
    assert normalize_text("the developer is building a project") == ["developer", "building", "project"]


def test_retriever_empty_repository():
    """Verify retrieval returns empty collection if repository is empty."""
    mock_repo = MagicMock(spec=MemoryRepository)
    mock_repo.list_all.return_value = []
    
    retriever = LexicalMemoryRetriever(mock_repo)
    result = retriever.retrieve("any query")
    
    assert result.total_candidates == 0
    assert len(result.matches) == 0
    assert result.selected_count == 0


def test_retriever_zero_overlap():
    """Verify zero overlap memories are excluded."""
    mock_repo = MagicMock(spec=MemoryRepository)
    mock_repo.list_all.return_value = [
        create_test_memory("mem_1", "The capital of France is Paris.")
    ]
    
    retriever = LexicalMemoryRetriever(mock_repo)
    result = retriever.retrieve("Python programming language")
    
    assert result.total_candidates == 1
    assert len(result.matches) == 0


def test_retriever_partial_overlap_and_bounded_lexical_score():
    """Verify partial overlaps are scored, and lexical score is bounded between 0 and 1."""
    mock_repo = MagicMock(spec=MemoryRepository)
    mem = create_test_memory("mem_1", "The user prefers Python programming.", importance=0.0)
    mock_repo.list_all.return_value = [mem]
    
    retriever = LexicalMemoryRetriever(mock_repo)
    # query: "prefers Python" -> normalized: ["prefers", "python"]
    # memory: "user prefers Python programming" -> normalized: ["user", "prefers", "python", "programming"]
    # overlap: ["prefers", "python"] (overlap_count = 2)
    # query_coverage = 2/2 = 1.0, mem_coverage = 2/4 = 0.5
    # lexical_score = 0.7 * 1.0 + 0.3 * 0.5 = 0.85
    result = retriever.retrieve("prefers Python")
    
    assert result.selected_count == 1
    match = result.matches[0]
    assert match.lexical_score == 0.85
    assert 0.0 <= match.lexical_score <= 1.0
    assert 0.0 <= match.relevance_score <= 1.0


def test_importance_contribution():
    """Verify importance score serves as secondary ranking signal."""
    mock_repo = MagicMock(spec=MemoryRepository)
    # Both memories have identical contents but different importance values
    mem_low = create_test_memory("mem_low", "Anas is building a software tool.", importance=0.1)
    mem_high = create_test_memory("mem_high", "Anas is building a software tool.", importance=0.9)
    mock_repo.list_all.return_value = [mem_low, mem_high]
    
    retriever = LexicalMemoryRetriever(mock_repo)
    result = retriever.retrieve("Anas software tool")
    
    assert result.selected_count == 2
    # mem_high should be ranked first due to higher importance score
    assert result.matches[0].memory.memory_id == "mem_high"
    assert result.matches[0].relevance_score > result.matches[1].relevance_score


def test_unrelated_high_importance_memory_excluded():
    """Verify high importance unrelated memories are excluded due to threshold."""
    mock_repo = MagicMock(spec=MemoryRepository)
    # High importance, but zero overlap
    mem_unrelated = create_test_memory("mem_1", "The capital of France is Paris.", importance=1.0)
    # Low importance, but partial overlap
    mem_related = create_test_memory("mem_2", "I love programming in Python.", importance=0.1)
    mock_repo.list_all.return_value = [mem_unrelated, mem_related]
    
    retriever = LexicalMemoryRetriever(mock_repo)
    result = retriever.retrieve("Python programming")
    
    # mem_unrelated has 0 overlap and should be excluded entirely
    assert result.selected_count == 1
    assert result.matches[0].memory.memory_id == "mem_2"


def test_limit_validation():
    """Verify limit validation throws error for non-positive bounds."""
    mock_repo = MagicMock(spec=MemoryRepository)
    retriever = LexicalMemoryRetriever(mock_repo)
    
    with pytest.raises(MemoryValidationError):
        retriever.retrieve("query", limit=0)
        
    with pytest.raises(MemoryValidationError):
        retriever.retrieve("query", limit=-5)


def test_bounded_retrieval_and_deterministic_ordering():
    """Verify top-K limit is applied and ties are resolved deterministically."""
    mock_repo = MagicMock(spec=MemoryRepository)
    
    # 3 identical memories except for updated_at / memory_id
    dt1 = datetime(2026, 7, 6, 10, 0, 0, tzinfo=timezone.utc)
    dt2 = datetime(2026, 7, 6, 11, 0, 0, tzinfo=timezone.utc)
    
    m1 = Memory("mem_a", "Anas prefers Python.", MemoryType.FACT, dt1, dt1, 0.5, MemorySource.MANUAL, {})
    m2 = Memory("mem_b", "Anas prefers Python.", MemoryType.FACT, dt2, dt2, 0.5, MemorySource.MANUAL, {})
    m3 = Memory("mem_c", "Anas prefers Python.", MemoryType.FACT, dt2, dt2, 0.5, MemorySource.MANUAL, {})
    
    mock_repo.list_all.return_value = [m1, m2, m3]
    retriever = LexicalMemoryRetriever(mock_repo)
    
    # Sort order checks:
    # 1. Relevance descending (all identical)
    # 2. Importance descending (all identical)
    # 3. updated_at descending (m2 and m3 are newer than m1)
    # 4. memory_id ascending (mem_b should come before mem_c)
    result = retriever.retrieve("Anas prefers Python", limit=2)
    
    assert result.selected_count == 2
    assert result.matches[0].memory.memory_id == "mem_b"
    assert result.matches[1].memory.memory_id == "mem_c"
