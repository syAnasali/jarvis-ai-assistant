"""Local Vector Store supporting vector cosine similarity search and metadata filtering."""

import math
from typing import Any, Dict, List, Optional, Tuple
from app.core.logger import JarvisLogger
from app.knowledge.interfaces import VectorStore
from app.knowledge.models import DocumentChunk, IndexStatus

logger = JarvisLogger.get_logger("vector_store")


class LocalVectorStore(VectorStore):
    """Local vector store performing cosine similarity search over embedded chunks."""

    def __init__(self, repository: Optional[Any] = None) -> None:
        self.repository = repository
        self._chunks: Dict[str, DocumentChunk] = {}
        self._load_chunks_from_repo()

    def _load_chunks_from_repo(self) -> None:
        """Loads existing chunks and embeddings from SQLite repository if available."""
        if self.repository:
            try:
                repo_chunks = self.repository.get_all_chunks()
                for c in repo_chunks:
                    self._chunks[c.chunk_id] = c
                logger.info(f"Loaded {len(self._chunks)} chunks into LocalVectorStore index.")
            except Exception as e:
                logger.warning(f"Error loading chunks from repository: {e}")

    def add_chunks(self, chunks: List[DocumentChunk]) -> None:
        """Indexes document chunks into the vector store."""
        for c in chunks:
            self._chunks[c.chunk_id] = c

        if self.repository:
            self.repository.save_chunks(chunks)

        logger.info(f"Added {len(chunks)} chunks to LocalVectorStore.")

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[DocumentChunk, float]]:
        """Performs vector cosine similarity search."""
        results: List[Tuple[DocumentChunk, float]] = []
        q_norm = math.sqrt(sum(x * x for x in query_embedding))
        if q_norm == 0:
            return []

        filters = filters or {}

        for chunk in self._chunks.values():
            if not chunk.embedding:
                continue

            # Apply metadata filters
            match_filters = True
            for fk, fv in filters.items():
                if chunk.metadata.get(fk) != fv:
                    match_filters = False
                    break

            if not match_filters:
                continue

            # Cosine Similarity calculation
            emb = chunk.embedding
            dot = sum(q * e for q, e in zip(query_embedding, emb))
            e_norm = math.sqrt(sum(e * e for e in emb))
            sim = dot / (q_norm * e_norm) if (q_norm * e_norm) > 0 else 0.0

            results.append((chunk, float(sim)))

        # Sort descending by similarity score
        results.sort(key=lambda item: item[1], reverse=True)
        return results[:top_k]

    def delete_document(self, document_id: str) -> None:
        """Deletes all chunks belonging to document_id."""
        to_delete = [cid for cid, c in self._chunks.items() if c.document_id == document_id]
        for cid in to_delete:
            del self._chunks[cid]

        if self.repository:
            self.repository.delete_document(document_id)

        logger.info(f"Deleted document '{document_id}' ({len(to_delete)} chunks) from LocalVectorStore.")

    def get_status(self) -> IndexStatus:
        """Returns index metrics."""
        unique_docs = len(set(c.document_id for c in self._chunks.values()))
        total_size = sum(len(c.content.encode("utf-8")) for c in self._chunks.values())
        return IndexStatus(
            total_documents=unique_docs,
            total_chunks=len(self._chunks),
            index_size_bytes=total_size,
            embedding_model="local-vector-index",
            status_message=f"Indexed {len(self._chunks)} chunks across {unique_docs} documents."
        )
