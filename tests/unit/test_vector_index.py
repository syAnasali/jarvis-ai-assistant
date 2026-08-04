"""Unit tests for LocalVectorStore."""

import pytest
from app.knowledge.index import LocalVectorStore
from app.knowledge.models import DocumentChunk


def test_local_vector_store_add_and_search():
    store = LocalVectorStore()
    c1 = DocumentChunk(document_id="d1", content="Chunk 1", chunk_index=0, embedding=(1.0, 0.0, 0.0))
    c2 = DocumentChunk(document_id="d2", content="Chunk 2", chunk_index=0, embedding=(0.0, 1.0, 0.0))

    store.add_chunks([c1, c2])

    matches = store.search([1.0, 0.0, 0.0], top_k=1)
    assert len(matches) == 1
    assert matches[0][0].chunk_id == c1.chunk_id
    assert matches[0][1] == pytest.approx(1.0)
