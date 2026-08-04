"""Unit tests verifying strict memory isolation between RAG document chunks and Long-Term Memory."""

import pytest
from app.memory.validation import MemoryEvidenceValidator
from app.memory.models import MemoryCandidate, MemoryType, MemorySource
from app.knowledge.models import DocumentChunk


def test_rag_chunk_is_isolated_from_automatic_memory_persistence():
    chunk = DocumentChunk(
        document_id="doc_os",
        content="Operating Systems Virtual Memory page tables and segment replacement algorithms.",
        chunk_index=0
    )

    # RAG document chunk without first-person user claim MUST fail memory evidence validation
    candidate = MemoryCandidate(
        content=chunk.content,
        memory_type=MemoryType.FACT,
        importance=0.5,
        confidence=0.9,
        source=MemorySource.SYSTEM,
        evidence=chunk.content
    )
    validator = MemoryEvidenceValidator()

    # Must return False (rejected by memory validation rules)
    is_valid = validator.validate(candidate, source_text=chunk.content)
    assert is_valid is False
