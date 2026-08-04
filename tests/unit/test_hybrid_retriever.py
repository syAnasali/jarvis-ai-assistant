"""Unit tests for HybridRetrieverEngine."""

import pytest
from app.knowledge.embeddings import LocalHashEmbeddingProvider
from app.knowledge.index import LocalVectorStore
from app.knowledge.models import DocumentChunk, KnowledgeQuery
from app.knowledge.retriever import HybridRetrieverEngine


def test_hybrid_retriever_combines_scores():
    provider = LocalHashEmbeddingProvider()
    store = LocalVectorStore()
    emb = provider.embed_text("Deep Learning AI")

    c = DocumentChunk(document_id="d1", content="Deep Learning AI Notes", chunk_index=0, embedding=tuple(emb))
    store.add_chunks([c])

    retriever = HybridRetrieverEngine(vector_store=store, embedding_provider=provider)
    query = KnowledgeQuery(query_text="Deep Learning AI", top_k=1, alpha=0.5)

    results = retriever.retrieve(query)
    assert len(results) == 1
    assert results[0].score > 0.0
