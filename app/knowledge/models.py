"""Immutable domain models and dataclasses for the Personal Knowledge Base (RAG) subsystem."""

import copy
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Any, Dict, List, Optional, Tuple


class DocumentFormat(Enum):
    """Supported document file classifications."""
    PDF = "PDF"
    DOCX = "DOCX"
    TXT = "TXT"
    MARKDOWN = "MARKDOWN"
    HTML = "HTML"
    JSON = "JSON"
    CSV = "CSV"
    CODE = "CODE"
    GIT_REPO = "GIT_REPO"


class ChunkStrategy(Enum):
    """Text chunking strategies."""
    PARAGRAPH = "PARAGRAPH"
    SEMANTIC = "SEMANTIC"
    RECURSIVE = "RECURSIVE"
    CODE_AWARE = "CODE_AWARE"


@dataclass(frozen=True)
class Document:
    """Represents an ingested document."""
    file_path: str
    format: DocumentFormat
    title: str
    raw_content: str
    document_id: str = field(default_factory=lambda: f"doc_{uuid.uuid4().hex[:8]}")
    char_count: int = 0
    file_size_bytes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    ingested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.file_path.strip():
            raise ValueError("Document file_path cannot be empty.")
        if not self.title.strip():
            raise ValueError("Document title cannot be empty.")
        if self.ingested_at.tzinfo is None:
            raise ValueError("Document ingested_at must be timezone-aware.")
        c_count = len(self.raw_content)
        object.__setattr__(self, "char_count", c_count)
        object.__setattr__(self, "metadata", MappingProxyType(copy.deepcopy(self.metadata)))


@dataclass(frozen=True)
class DocumentChunk:
    """Represents a chunk extracted from a document."""
    document_id: str
    content: str
    chunk_index: int
    chunk_id: str = field(default_factory=lambda: f"chk_{uuid.uuid4().hex[:8]}")
    page_number: Optional[int] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    embedding: Optional[Tuple[float, ...]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise ValueError("DocumentChunk content cannot be empty.")
        if self.embedding is not None:
            object.__setattr__(self, "embedding", tuple(self.embedding))
        object.__setattr__(self, "metadata", MappingProxyType(copy.deepcopy(self.metadata)))


@dataclass(frozen=True)
class KnowledgeQuery:
    """Represents a search query issued to the RAG subsystem."""
    query_text: str
    top_k: int = 5
    alpha: float = 0.7  # 1.0 = pure vector similarity, 0.0 = pure keyword BM25
    filters: Dict[str, Any] = field(default_factory=dict)
    strategy: ChunkStrategy = ChunkStrategy.RECURSIVE

    def __post_init__(self) -> None:
        if not self.query_text.strip():
            raise ValueError("KnowledgeQuery text cannot be empty.")
        object.__setattr__(self, "filters", MappingProxyType(copy.deepcopy(self.filters)))


@dataclass(frozen=True)
class RetrievalResult:
    """Scored search match result with chunk and document reference."""
    chunk: DocumentChunk
    score: float
    semantic_score: float = 0.0
    keyword_score: float = 0.0
    source_document: Optional[Document] = None


@dataclass(frozen=True)
class Citation:
    """Structured citation metadata for RAG response attribution."""
    citation_id: str
    document_title: str
    file_path: str
    file_url: str  # Clickable file:/// scheme URL
    page_number: Optional[int] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    snippet: str = ""


@dataclass(frozen=True)
class IndexStatus:
    """Diagnostic status metrics of the vector store index."""
    total_documents: int
    total_chunks: int
    index_size_bytes: int
    embedding_model: str
    status_message: str
