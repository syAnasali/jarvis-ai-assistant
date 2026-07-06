"""Diagnostics script to verify memory conflict resolution logic."""

import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.memory.models import Memory, MemoryCandidate, MemoryType, MemorySource
from app.memory.write_service import MemoryWriteService
from app.memory.manager import MemoryManager
from app.memory.resolution import (
    MemoryResolutionAction,
    MemoryResolutionDecision,
    MemoryResolutionExecutor,
    MemoryResolutionValidator,
)
from app.memory.related import RelatedMemoryFinder
from app.memory.interfaces import MemoryResolver, MemoryExtractor, MemoryExtractionResult


def run_diagnostics():
    print("==========================================================")
    print("RUNNING MEMORY CONFLICT RESOLUTION DIAGNOSTICS")
    print("==========================================================")

    # 1. Mock Extraction
    mock_extractor = MagicMock(spec=MemoryExtractor)
    cand = MemoryCandidate(
        content="The user prefers JavaScript for backend.",
        memory_type=MemoryType.PREFERENCE,
        importance=0.8,
        confidence=0.95,
        source=MemorySource.USER,
        evidence="I prefer JavaScript on the backend now.",
        metadata={}
    )
    mock_extractor.extract.return_value = MemoryExtractionResult(
        candidates=(cand,),
        source_text="I prefer JavaScript on the backend now.",
        candidate_count=1
    )

    # 2. Existing Memory
    existing = Memory(
        memory_id="mem_pref_1",
        content="The user prefers Python for backend development.",
        memory_type=MemoryType.PREFERENCE,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        importance=0.75,
        source=MemorySource.USER,
        metadata={"extraction_method": "llm"}
    )

    mock_manager = MagicMock(spec=MemoryManager)
    mock_manager.list_memories.return_value = [existing]
    mock_manager.get_memory.return_value = existing

    # 3. Mock Resolver returning UPDATE
    mock_resolver = MagicMock(spec=MemoryResolver)
    mock_resolver.resolve.return_value = MemoryResolutionDecision(
        action=MemoryResolutionAction.UPDATE,
        candidate=cand,
        target_memory_id="mem_pref_1",
        confidence=0.98,
        reason_code="UPDATED_PREFERENCE"
    )

    # 4. Initialize Write Service
    service = MemoryWriteService(
        extractor=mock_extractor,
        memory_manager=mock_manager,
        resolver=mock_resolver
    )

    print("Executing write_memories with a conflict...")
    result = service.write_memories("I prefer JavaScript on the backend now.")

    print(f"Extracted count: {result.extracted_count}")
    print(f"Persisted count: {result.persisted_count}")
    print(f"Updated count: {result.updated_count}")
    print(f"Duplicate count: {result.duplicate_count}")
    print(f"Rejected count: {result.rejected_count}")
    print(f"Resolution failed count: {result.resolution_failed_count}")

    assert result.extracted_count == 1
    assert result.persisted_count == 1
    assert result.updated_count == 1
    
    print("SUCCESS: Memory conflict resolution diagnostics completed successfully!")
    print("==========================================================")


if __name__ == "__main__":
    run_diagnostics()
