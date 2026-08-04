"""Unit tests for ResultRerankerEngine."""

import pytest
from app.knowledge.models import DocumentChunk, KnowledgeQuery, RetrievalResult
from app.knowledge.reranker import ResultRerankerEngine


def test_result_reranker_phrase_boost():
    reranker = ResultRerankerEngine()
    c1 = DocumentChunk(document_id="d1", content="Machine Learning Algorithms", chunk_index=0)
    c2 = DocumentChunk(document_id="d2", content="Unrelated topic", chunk_index=0)

    r1 = RetrievalResult(chunk=c1, score=0.5)
    r2 = RetrievalResult(chunk=c2, score=0.5)

    query = KnowledgeQuery(query_text="Machine Learning")
    reranked = reranker.rerank(query, [r1, r2])

    assert reranked[0].chunk.document_id == "d1"
    assert reranked[0].score > reranked[1].score
