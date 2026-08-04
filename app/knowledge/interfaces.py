"""Abstract interface contracts for the Personal Knowledge Base (RAG) subsystem."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from app.knowledge.models import (
    Citation,
    Document,
    DocumentChunk,
    DocumentFormat,
    IndexStatus,
    KnowledgeQuery,
    RetrievalResult,
)


class DocumentParser(ABC):
    """Abstract interface for parsing files into structured Documents."""

    @abstractmethod
    def can_parse(self, file_path: str) -> bool:
        """Returns True if this parser supports the target file_path format."""
        pass

    @abstractmethod
    def parse(self, file_path: str) -> Document:
        """Parses a file into a Document container."""
        pass


class TextChunker(ABC):
    """Abstract interface for chunking documents into search segments."""

    @abstractmethod
    def chunk(self, document: Document, chunk_size: int = 512, overlap: int = 64) -> List[DocumentChunk]:
        """Splits document text into DocumentChunk instances."""
        pass


class EmbeddingProvider(ABC):
    """Abstract interface for generating text embedding vectors."""

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Generates a dense vector embedding for a text string."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generates dense vector embeddings for a batch of text strings."""
        pass


class VectorStore(ABC):
    """Abstract interface for local vector storage and similarity search."""

    @abstractmethod
    def add_chunks(self, chunks: List[DocumentChunk]) -> None:
        """Indexes a list of DocumentChunks into the vector store."""
        pass

    @abstractmethod
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[DocumentChunk, float]]:
        """Performs vector similarity search."""
        pass

    @abstractmethod
    def delete_document(self, document_id: str) -> None:
        """Removes a document's chunks from the vector store."""
        pass


class HybridRetriever(ABC):
    """Abstract interface for hybrid vector and keyword search retrieval."""

    @abstractmethod
    def retrieve(self, query: KnowledgeQuery) -> List[RetrievalResult]:
        """Performs hybrid vector similarity and BM25 keyword search."""
        pass


class ResultReranker(ABC):
    """Abstract interface for scoring and re-ordering retrieval results."""

    @abstractmethod
    def rerank(self, query: KnowledgeQuery, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """Reranks candidate retrieval results for maximum relevance and diversity."""
        pass


class CitationFormatter(ABC):
    """Abstract interface for producing citations from retrieval matches."""

    @abstractmethod
    def format_citations(self, results: List[RetrievalResult]) -> List[Citation]:
        """Formats structured citations with clickable file URLs."""
        pass
