"""Result Reranker Engine scoring candidate relevance, exact match density, and document diversity."""

import re
from typing import List
from app.core.logger import JarvisLogger
from app.knowledge.interfaces import ResultReranker
from app.knowledge.models import KnowledgeQuery, RetrievalResult

logger = JarvisLogger.get_logger("result_reranker")


class ResultRerankerEngine(ResultReranker):
    """Reranks candidate retrieval results for optimal score alignment and diversity."""

    def rerank(self, query: KnowledgeQuery, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """Reranks candidate matches using query term match density and diversity penalties."""
        if not results:
            return []

        logger.info(f"Reranking {len(results)} candidate results...")
        query_words = set(re.findall(r"\w+", query.query_text.lower()))

        reranked: List[RetrievalResult] = []
        seen_docs: dict[str, int] = {}

        for res in results:
            content_lower = res.chunk.content.lower()

            # 1. Exact phrase boost
            phrase_boost = 0.2 if query.query_text.lower() in content_lower else 0.0

            # 2. Document diversity penalty if multiple chunks from same document
            doc_id = res.chunk.document_id
            seen_count = seen_docs.get(doc_id, 0)
            diversity_penalty = 0.05 * seen_count
            seen_docs[doc_id] = seen_count + 1

            final_score = max(0.0, res.score + phrase_boost - diversity_penalty)

            adjusted_res = RetrievalResult(
                chunk=res.chunk,
                score=final_score,
                semantic_score=res.semantic_score,
                keyword_score=res.keyword_score,
                source_document=res.source_document
            )
            reranked.append(adjusted_res)

        reranked.sort(key=lambda r: r.score, reverse=True)
        return reranked
