"""Unit tests for the MemoryWriteService class."""

import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone

from app.core.exceptions import MemoryPersistenceError, MemorySystemError
from app.memory.interfaces import MemoryExtractor
from app.memory.models import (
    Memory,
    MemoryType,
    MemorySource,
    MemoryCandidate,
    MemoryExtractionResult
)
from app.memory.manager import MemoryManager
from app.memory.write_service import MemoryWriteService


def create_test_candidate(
    content: str,
    conf: float = 0.9,
    memory_type: MemoryType = MemoryType.FACT,
    evidence: str = "My name is Anas"
) -> MemoryCandidate:
    """Helper to construct dummy candidates."""
    return MemoryCandidate(
        content=content,
        memory_type=memory_type,
        importance=0.8,
        confidence=conf,
        source=MemorySource.USER,
        evidence=evidence,
        metadata={}
    )


def create_test_memory(content: str, memory_type: MemoryType = MemoryType.FACT) -> Memory:
    """Helper to construct dummy stored memories."""
    return Memory(
        memory_id="mem_123",
        content=content,
        memory_type=memory_type,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        importance=0.8,
        source=MemorySource.USER,
        metadata={}
    )


def test_write_service_no_candidates():
    """Verify empty candidates result in 0 counts."""
    mock_extractor = MagicMock(spec=MemoryExtractor)
    mock_extractor.extract.return_value = MemoryExtractionResult(candidates=(), source_text="Query", candidate_count=0)

    mock_manager = MagicMock(spec=MemoryManager)
    mock_manager.list_memories.return_value = []

    service = MemoryWriteService(mock_extractor, mock_manager)
    res = service.write_memories("Query")

    assert res.extracted_count == 0
    assert res.persisted_count == 0
    assert res.duplicate_count == 0
    assert res.rejected_count == 0


def test_write_service_candidate_persisted():
    """Verify standard candidate is successfully persisted."""
    mock_extractor = MagicMock(spec=MemoryExtractor)
    cand = create_test_candidate("The user's name is Anas.", evidence="My name is Anas")
    mock_extractor.extract.return_value = MemoryExtractionResult(candidates=(cand,), source_text="My name is Anas", candidate_count=1)

    mock_manager = MagicMock(spec=MemoryManager)
    mock_manager.list_memories.return_value = []
    
    stored = Memory("m_1", cand.content, cand.memory_type, datetime.now(timezone.utc), datetime.now(timezone.utc), cand.importance, cand.source, {})
    mock_manager.create_memory.return_value = stored

    service = MemoryWriteService(mock_extractor, mock_manager)
    res = service.write_memories("My name is Anas")

    assert res.extracted_count == 1
    assert res.persisted_count == 1
    assert res.persisted_memory_ids == ("m_1",)
    mock_manager.create_memory.assert_called_once_with(
        content=cand.content,
        memory_type=cand.memory_type,
        importance=cand.importance,
        source=MemorySource.USER,
        metadata={"extraction_method": "llm", "source": "agent_request"}
    )


def test_write_service_low_confidence_candidate_rejected():
    """Verify candidate below confidence threshold is rejected."""
    mock_extractor = MagicMock(spec=MemoryExtractor)
    # Default threshold: 0.8. Confidence: 0.75
    cand = create_test_candidate("The user's name is Anas", conf=0.75, evidence="My name is Anas")
    mock_extractor.extract.return_value = MemoryExtractionResult(candidates=(cand,), source_text="My name is Anas", candidate_count=1)

    mock_manager = MagicMock(spec=MemoryManager)
    service = MemoryWriteService(mock_extractor, mock_manager, confidence_threshold=0.8)
    res = service.write_memories("My name is Anas")

    assert res.persisted_count == 0
    assert res.rejected_count == 1
    mock_manager.create_memory.assert_not_called()


def test_write_service_exact_and_normalized_duplicates_detected():
    """Verify case, whitespace, and punctuation variations are detected as duplicates."""
    mock_extractor = MagicMock(spec=MemoryExtractor)
    existing = create_test_memory("The user prefers Python.", MemoryType.PREFERENCE)
    
    mock_manager = MagicMock(spec=MemoryManager)
    mock_manager.list_memories.return_value = [existing]

    # Test cases for exact duplicates
    dup_cases = [
        "The user prefers Python.",
        "  the user prefers python.  ",
        "The   user   prefers   Python!",
        "the user prefers python"
    ]

    for case in dup_cases:
        cand = create_test_candidate(case, memory_type=MemoryType.PREFERENCE, evidence="I prefer Python")
        mock_extractor.extract.return_value = MemoryExtractionResult(candidates=(cand,), source_text="I prefer Python", candidate_count=1)
        
        service = MemoryWriteService(mock_extractor, mock_manager)
        res = service.write_memories("I prefer Python")
        
        assert res.duplicate_count == 1, f"Failed duplicate check for case: '{case}'"
        assert res.persisted_count == 0


def test_write_service_same_content_different_type_not_duplicate():
    """Verify identical content but different MemoryType is NOT suppressed as duplicate."""
    mock_extractor = MagicMock(spec=MemoryExtractor)
    cand = create_test_candidate("Anas is building Jarvis.", memory_type=MemoryType.PROJECT, evidence="I am building Jarvis")
    mock_extractor.extract.return_value = MemoryExtractionResult(candidates=(cand,), source_text="I am building Jarvis", candidate_count=1)

    # Existing memory of type FACT
    existing = create_test_memory("Anas is building Jarvis.", memory_type=MemoryType.FACT)
    mock_manager = MagicMock(spec=MemoryManager)
    mock_manager.list_memories.return_value = [existing]
    
    stored = Memory("m_p", cand.content, cand.memory_type, datetime.now(timezone.utc), datetime.now(timezone.utc), cand.importance, cand.source, {})
    mock_manager.create_memory.return_value = stored

    service = MemoryWriteService(mock_extractor, mock_manager)
    res = service.write_memories("I am building Jarvis")

    assert res.persisted_count == 1
    assert res.duplicate_count == 0


def test_write_service_near_duplicate_conservative_deduplication():
    """Verify near-duplicates with identical token sets are resolved, but different keywords are preserved."""
    mock_extractor = MagicMock(spec=MemoryExtractor)
    
    existing1 = create_test_memory("Anas prefers Python.", MemoryType.PREFERENCE)
    cand1 = create_test_candidate("Python prefers Anas.", memory_type=MemoryType.PREFERENCE, evidence="I prefer Python")
    
    mock_manager = MagicMock(spec=MemoryManager)
    mock_manager.list_memories.return_value = [existing1]
    
    service = MemoryWriteService(mock_extractor, mock_manager)
    mock_extractor.extract.return_value = MemoryExtractionResult(candidates=(cand1,), source_text="I prefer Python", candidate_count=1)
    res1 = service.write_memories("I prefer Python")
    assert res1.duplicate_count == 1
    assert res1.persisted_count == 0

    # Case 2: Different values (Java vs Python) - must be preserved
    existing2 = create_test_memory("The user prefers Python.", MemoryType.PREFERENCE)
    cand2 = create_test_candidate("The user prefers Java.", memory_type=MemoryType.PREFERENCE, evidence="I prefer Java")
    mock_manager.list_memories.return_value = [existing2]
    
    stored = Memory("m_2", cand2.content, cand2.memory_type, datetime.now(timezone.utc), datetime.now(timezone.utc), cand2.importance, cand2.source, {})
    mock_manager.create_memory.return_value = stored
    
    mock_extractor.extract.return_value = MemoryExtractionResult(candidates=(cand2,), source_text="I prefer Java", candidate_count=1)
    res2 = service.write_memories("I prefer Java")
    
    assert res2.persisted_count == 1
    assert res2.duplicate_count == 0


def test_write_service_secrets_rejected():
    """Verify credentials and secret patterns are rejected by secret guard."""
    mock_extractor = MagicMock(spec=MemoryExtractor)
    mock_manager = MagicMock(spec=MemoryManager)
    mock_manager.list_memories.return_value = []
    
    secret_contents = [
        "My password is supersecret123",
        "Authorization: Bearer abcd1234efgh5678",
        "sk-proj-abcdefghijklmnop1234567890",
        "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA..."
    ]

    service = MemoryWriteService(mock_extractor, mock_manager)

    for secret in secret_contents:
        cand = create_test_candidate(secret, evidence=secret)
        mock_extractor.extract.return_value = MemoryExtractionResult(candidates=(cand,), source_text=secret, candidate_count=1)
        res = service.write_memories(secret)
        
        assert res.persisted_count == 0
        assert res.rejected_count == 1
        mock_manager.create_memory.assert_not_called()


def test_write_service_repository_failure_propagates():
    """Verify database write failure throws MemoryPersistenceError."""
    mock_extractor = MagicMock(spec=MemoryExtractor)
    cand = create_test_candidate("The user prefers Python.", memory_type=MemoryType.PREFERENCE, evidence="I prefer Python")
    mock_extractor.extract.return_value = MemoryExtractionResult(candidates=(cand,), source_text="I prefer Python", candidate_count=1)

    mock_manager = MagicMock(spec=MemoryManager)
    mock_manager.list_memories.return_value = []
    mock_manager.create_memory.side_effect = RuntimeError("SQLite database is locked")

    service = MemoryWriteService(mock_extractor, mock_manager)
    
    with pytest.raises(MemoryPersistenceError):
        service.write_memories("I prefer Python")


def test_write_service_fabricated_evidence_rejected():
    """Verify candidate with evidence not present in source is rejected."""
    mock_extractor = MagicMock(spec=MemoryExtractor)
    cand = create_test_candidate("The user's name is Anas.", evidence="My name is Anas")
    # Source text does NOT contain "My name is Anas"
    mock_extractor.extract.return_value = MemoryExtractionResult(candidates=(cand,), source_text="Hello world", candidate_count=1)

    mock_manager = MagicMock(spec=MemoryManager)
    mock_manager.list_memories.return_value = []

    service = MemoryWriteService(mock_extractor, mock_manager)
    res = service.write_memories("Hello world")

    assert res.persisted_count == 0
    assert res.rejected_count == 1
