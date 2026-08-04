"""SQLite Knowledge Repository for durable document catalog and vector chunk persistence."""

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.core.logger import JarvisLogger
from app.knowledge.models import Document, DocumentChunk, DocumentFormat

logger = JarvisLogger.get_logger("knowledge_repository")


class SQLiteKnowledgeRepository:
    """Persists documents, chunks, and embeddings to SQLite database."""

    def __init__(self, database_path: str = "data/jarvis.db") -> None:
        self.db_path = database_path
        self._mem_conn: Optional[sqlite3.Connection] = None
        if self.db_path == ":memory:":
            self._mem_conn = sqlite3.connect(":memory:")
            self._mem_conn.row_factory = sqlite3.Row
        self._initialize_schema()

    def _get_connection(self) -> sqlite3.Connection:
        if self._mem_conn is not None:
            return self._mem_conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize_schema(self) -> None:
        """Initializes database schema for Knowledge Base repository."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_documents (
                    document_id TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    format TEXT NOT NULL,
                    title TEXT NOT NULL,
                    char_count INTEGER NOT NULL,
                    file_size_bytes INTEGER NOT NULL,
                    metadata_json TEXT NOT NULL,
                    ingested_at TEXT NOT NULL,
                    raw_content TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_chunks (
                    chunk_id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    page_number INTEGER,
                    start_line INTEGER,
                    end_line INTEGER,
                    embedding_json TEXT,
                    metadata_json TEXT NOT NULL,
                    FOREIGN KEY (document_id) REFERENCES knowledge_documents (document_id) ON DELETE CASCADE
                )
            """)
            conn.commit()

    def save_document(self, doc: Document) -> None:
        """Saves or updates a Document record."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO knowledge_documents (
                    document_id, file_path, format, title, char_count, file_size_bytes, metadata_json, ingested_at, raw_content
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(document_id) DO UPDATE SET
                    title=excluded.title,
                    char_count=excluded.char_count,
                    raw_content=excluded.raw_content
                """,
                (
                    doc.document_id,
                    doc.file_path,
                    doc.format.value,
                    doc.title,
                    doc.char_count,
                    doc.file_size_bytes,
                    json.dumps(dict(doc.metadata)),
                    doc.ingested_at.isoformat(),
                    doc.raw_content
                )
            )
            conn.commit()

    def save_chunks(self, chunks: List[DocumentChunk]) -> None:
        """Saves a batch of DocumentChunks."""
        with self._get_connection() as conn:
            for chunk in chunks:
                emb_json = json.dumps(list(chunk.embedding)) if chunk.embedding is not None else None
                conn.execute(
                    """
                    INSERT INTO knowledge_chunks (
                        chunk_id, document_id, chunk_index, content, page_number,
                        start_line, end_line, embedding_json, metadata_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(chunk_id) DO UPDATE SET
                        content=excluded.content,
                        embedding_json=excluded.embedding_json
                    """,
                    (
                        chunk.chunk_id,
                        chunk.document_id,
                        chunk.chunk_index,
                        chunk.content,
                        chunk.page_number,
                        chunk.start_line,
                        chunk.end_line,
                        emb_json,
                        json.dumps(dict(chunk.metadata))
                    )
                )
            conn.commit()

    def get_document(self, document_id: str) -> Optional[Document]:
        """Retrieves a document by document_id."""
        with self._get_connection() as conn:
            r = conn.execute("SELECT * FROM knowledge_documents WHERE document_id = ?", (document_id,)).fetchone()
            if not r:
                return None

            return Document(
                document_id=r["document_id"],
                file_path=r["file_path"],
                format=DocumentFormat(r["format"]),
                title=r["title"],
                raw_content=r["raw_content"],
                file_size_bytes=r["file_size_bytes"],
                metadata=json.loads(r["metadata_json"]),
                ingested_at=datetime.fromisoformat(r["ingested_at"])
            )

    def list_documents(self) -> List[Document]:
        """Lists all ingested documents."""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT document_id FROM knowledge_documents ORDER BY ingested_at DESC").fetchall()
            docs: List[Document] = []
            for r in rows:
                doc = self.get_document(r["document_id"])
                if doc:
                    docs.append(doc)
            return docs

    def get_all_chunks(self) -> List[DocumentChunk]:
        """Retrieves all document chunks with embeddings."""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM knowledge_chunks").fetchall()
            chunks: List[DocumentChunk] = []
            for r in rows:
                emb = json.loads(r["embedding_json"]) if r["embedding_json"] else None
                chunk = DocumentChunk(
                    chunk_id=r["chunk_id"],
                    document_id=r["document_id"],
                    chunk_index=r["chunk_index"],
                    content=r["content"],
                    page_number=r["page_number"],
                    start_line=r["start_line"],
                    end_line=r["end_line"],
                    embedding=tuple(emb) if emb else None,
                    metadata=json.loads(r["metadata_json"])
                )
                chunks.append(chunk)
            return chunks

    def delete_document(self, document_id: str) -> None:
        """Deletes a document and its chunks from SQLite."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM knowledge_chunks WHERE document_id = ?", (document_id,))
            conn.execute("DELETE FROM knowledge_documents WHERE document_id = ?", (document_id,))
            conn.commit()
