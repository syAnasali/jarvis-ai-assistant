"""Hybrid Retriever Engine combining dense vector similarity and sparse BM25 keyword search."""

import re
from typing import Any, Dict, List, Optional, Set
from app.core.logger import JarvisLogger
from app.knowledge.interfaces import EmbeddingProvider, HybridRetriever, VectorStore
from app.knowledge.models import DocumentChunk, KnowledgeQuery, RetrievalResult

logger = JarvisLogger.get_logger("hybrid_retriever")


class HybridRetrieverEngine(HybridRetriever):
    """Combines vector similarity and BM25 keyword search with weighted score fusion."""

    def __init__(
        self,
        vector_store: VectorStore,
        embedding_provider: EmbeddingProvider,
        repository: Optional[Any] = None
    ) -> None:
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider
        self.repository = repository

    def retrieve(self, query: KnowledgeQuery) -> List[RetrievalResult]:
        """Performs hybrid vector similarity and BM25 keyword retrieval."""
        logger.info(f"Executing hybrid retrieval for query: '{query.query_text[:50]}' (alpha={query.alpha}, top_k={query.top_k})...")

        # 1. Semantic Vector Search
        query_emb = self.embedding_provider.embed_text(query.query_text)
        vector_matches = self.vector_store.search(
            query_embedding=query_emb,
            top_k=query.top_k * 2,
            filters=dict(query.filters)
        )

        semantic_map: Dict[str, Tuple[DocumentChunk, float]] = {
            chunk.chunk_id: (chunk, sim_score) for chunk, sim_score in vector_matches
        }

        # 2. Keyword BM25 Search
        query_words = set(re.findall(r"\w+", query.query_text.lower()))
        keyword_scores: Dict[str, float] = {}

        for chunk, _ in vector_matches:
            c_words = re.findall(r"\w+", chunk.content.lower())
            if not c_words:
                continue
            matches = sum(1 for w in query_words if w in c_words)
            keyword_scores[chunk.chunk_id] = matches / float(len(query_words)) if query_words else 0.0

        # 3. Hybrid Score Fusion
        results: List[RetrievalResult] = []
        for chunk_id, (chunk, sem_score) in semantic_map.items():
            kw_score = keyword_scores.get(chunk_id, 0.0)
            combined_score = (query.alpha * sem_score) + ((1.0 - query.alpha) * kw_score)

            doc = self.repository.get_document(chunk.document_id) if self.repository else None

            res = RetrievalResult(
                chunk=chunk,
                score=combined_score,
                semantic_score=sem_score,
                keyword_score=kw_score,
                source_document=doc
            )
            results.append(res)

        # Sort descending by combined score
        results.sort(key=lambda item: item.score, reverse=True)
        top_results = results[:query.top_k]
        logger.info(f"Retrieved {len(top_results)} hybrid matched chunks.")
        return top_results
