"""Unit tests for Personal Knowledge Base domain models."""

import pytest
from app.knowledge.models import (
    DocumentFormat,
    ChunkStrategy,
    Document,
    DocumentChunk,
    KnowledgeQuery,
    RetrievalResult,
    Citation,
    IndexStatus,
)


def test_document_model_validation():
    doc = Document(file_path="C:\\Docs\\notes.txt", format=DocumentFormat.TXT, title="notes.txt", raw_content="Hello world")
    assert doc.title == "notes.txt"
    assert doc.char_count == 11

    with pytest.raises(ValueError):
        Document(file_path="", format=DocumentFormat.TXT, title="t", raw_content="c")


def test_document_chunk_validation():
    chunk = DocumentChunk(document_id="doc1", content="Chunk content", chunk_index=0)
    assert chunk.document_id == "doc1"
    assert chunk.content == "Chunk content"

    with pytest.raises(ValueError):
        DocumentChunk(document_id="doc1", content="", chunk_index=0)


def test_knowledge_query_validation():
    q = KnowledgeQuery(query_text="AI Research", top_k=3, alpha=0.8)
    assert q.top_k == 3
    assert q.alpha == 0.8

    with pytest.raises(ValueError):
        KnowledgeQuery(query_text="")
