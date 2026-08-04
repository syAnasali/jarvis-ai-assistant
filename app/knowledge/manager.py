"""Knowledge Manager subsystem coordinator and telemetry tracker."""

from typing import Any, Dict, List, Optional, Tuple
from app.core.logger import JarvisLogger
from app.knowledge.citations import StructuredCitationFormatter
from app.knowledge.embeddings import LocalHashEmbeddingProvider
from app.knowledge.index import LocalVectorStore
from app.knowledge.ingestion import IngestionPipeline
from app.knowledge.models import (
    Citation,
    ChunkStrategy,
    Document,
    KnowledgeQuery,
    RetrievalResult,
)
from app.knowledge.repository import SQLiteKnowledgeRepository
from app.knowledge.reranker import ResultRerankerEngine
from app.knowledge.retriever import HybridRetrieverEngine

logger = JarvisLogger.get_logger("knowledge_manager")


class KnowledgeManager:
    """Orchestrates Personal Knowledge Base (RAG) subsystem components with telemetry metrics."""

    def __init__(
        self,
        repository: Optional[SQLiteKnowledgeRepository] = None,
        vector_store: Optional[LocalVectorStore] = None,
        embedding_provider: Optional[Any] = None,
        ingestion_pipeline: Optional[IngestionPipeline] = None,
        retriever: Optional[HybridRetrieverEngine] = None,
        reranker: Optional[ResultRerankerEngine] = None,
        citation_formatter: Optional[StructuredCitationFormatter] = None
    ) -> None:
        self.repository = repository or SQLiteKnowledgeRepository()
        self.vector_store = vector_store or LocalVectorStore(repository=self.repository)
        self.embedding_provider = embedding_provider or LocalHashEmbeddingProvider()

        self.pipeline = ingestion_pipeline or IngestionPipeline(
            embedding_provider=self.embedding_provider,
            vector_store=self.vector_store,
            repository=self.repository
        )
        self.retriever = retriever or HybridRetrieverEngine(
            vector_store=self.vector_store,
            embedding_provider=self.embedding_provider,
            repository=self.repository
        )
        self.reranker = reranker or ResultRerankerEngine()
        self.citation_formatter = citation_formatter or StructuredCitationFormatter()

        self.metrics: Dict[str, Any] = {
            "documents_ingested": 0,
            "queries_executed": 0,
            "total_matches_returned": 0
        }
        self._is_initialized = False

    def initialize(self) -> None:
        """Initializes KnowledgeManager components."""
        if self._is_initialized:
            return
        logger.info("Initializing KnowledgeManager components...")
        self._is_initialized = True
        logger.info("KnowledgeManager initialized successfully.")

    def ingest_document(
        self,
        file_path: str,
        chunk_strategy: Optional[ChunkStrategy] = None
    ) -> Document:
        """Ingests, parses, chunks, embeds, and indexes a file path."""
        doc = self.pipeline.ingest_file(file_path, chunk_strategy=chunk_strategy)
        self.metrics["documents_ingested"] += 1
        return doc

    def query_knowledge(
        self,
        query_text: str,
        top_k: int = 5,
        alpha: float = 0.7,
        filters: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[RetrievalResult], List[Citation]]:
        """Queries the RAG Knowledge Base returning ranked results and structured citations."""
        logger.info(f"Issuing knowledge query: '{query_text}'...")
        query = KnowledgeQuery(query_text=query_text, top_k=top_k, alpha=alpha, filters=filters or {})

        candidates = self.retriever.retrieve(query)
        reranked = self.reranker.rerank(query, candidates)
        citations = self.citation_formatter.format_citations(reranked)

        self.metrics["queries_executed"] += 1
        self.metrics["total_matches_returned"] += len(reranked)
        return reranked, citations

    def summarize_document(self, file_path_or_id: str) -> str:
        """Generates a summary of an ingested document."""
        doc = self.repository.get_document(file_path_or_id)
        if not doc:
            docs = self.repository.list_documents()
            matching = [d for d in docs if file_path_or_id.lower() in d.file_path.lower() or file_path_or_id.lower() in d.title.lower()]
            doc = matching[0] if matching else None

        if not doc:
            return f"Document '{file_path_or_id}' not found in Knowledge Base."

        snippet = doc.raw_content[:800].replace("\n", " ")
        return f"[Summary of {doc.title} ({doc.format.value})]\n{snippet}..."

    def list_documents(self) -> List[Document]:
        """Lists all stored documents."""
        return self.repository.list_documents()

    def remove_document(self, document_id: str) -> None:
        """Deletes a document from vector index and repository."""
        self.vector_store.delete_document(document_id)

    def health_check(self) -> Dict[str, Any]:
        """Returns subsystem health check metrics."""
        idx_status = self.vector_store.get_status()
        return {
            "available": self._is_initialized,
            "metrics": self.metrics,
            "index_status": {
                "total_documents": idx_status.total_documents,
                "total_chunks": idx_status.total_chunks,
                "index_size_bytes": idx_status.index_size_bytes
            }
        }

    def shutdown(self) -> None:
        """Shuts down KnowledgeManager resources."""
        self._is_initialized = False
        logger.info("KnowledgeManager shutdown complete.")
