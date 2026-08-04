"""Personal Knowledge Base (RAG) Subsystem package exports."""

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
from app.knowledge.interfaces import (
    DocumentParser,
    TextChunker,
    EmbeddingProvider,
    VectorStore,
    HybridRetriever,
    ResultReranker,
    CitationFormatter,
)
from app.knowledge.parser import UnifiedDocumentParser, DocumentParseError
from app.knowledge.chunker import ConfigurableTextChunker
from app.knowledge.embeddings import LocalHashEmbeddingProvider, OllamaEmbeddingProvider
from app.knowledge.repository import SQLiteKnowledgeRepository
from app.knowledge.index import LocalVectorStore
from app.knowledge.retriever import HybridRetrieverEngine
from app.knowledge.reranker import ResultRerankerEngine
from app.knowledge.citations import StructuredCitationFormatter
from app.knowledge.ingestion import IngestionPipeline
from app.knowledge.manager import KnowledgeManager

__all__ = [
    "DocumentFormat",
    "ChunkStrategy",
    "Document",
    "DocumentChunk",
    "KnowledgeQuery",
    "RetrievalResult",
    "Citation",
    "IndexStatus",
    "DocumentParser",
    "TextChunker",
    "EmbeddingProvider",
    "VectorStore",
    "HybridRetriever",
    "ResultReranker",
    "CitationFormatter",
    "UnifiedDocumentParser",
    "DocumentParseError",
    "ConfigurableTextChunker",
    "LocalHashEmbeddingProvider",
    "OllamaEmbeddingProvider",
    "SQLiteKnowledgeRepository",
    "LocalVectorStore",
    "HybridRetrieverEngine",
    "ResultRerankerEngine",
    "StructuredCitationFormatter",
    "IngestionPipeline",
    "KnowledgeManager",
]
