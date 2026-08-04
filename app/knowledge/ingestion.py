"""Ingestion Pipeline orchestrating Parse -> Chunk -> Embed -> Vector Indexing lifecycle."""

from typing import List, Optional
from app.core.logger import JarvisLogger
from app.knowledge.chunker import ConfigurableTextChunker
from app.knowledge.embeddings import LocalHashEmbeddingProvider
from app.knowledge.index import LocalVectorStore
from app.knowledge.interfaces import EmbeddingProvider, TextChunker, VectorStore
from app.knowledge.models import ChunkStrategy, Document, DocumentChunk
from app.knowledge.parser import UnifiedDocumentParser
from app.knowledge.repository import SQLiteKnowledgeRepository

logger = JarvisLogger.get_logger("ingestion_pipeline")


class IngestionPipeline:
    """Orchestrates intake, parsing, chunking, embedding, and vector indexing."""

    def __init__(
        self,
        parser: Optional[UnifiedDocumentParser] = None,
        chunker: Optional[TextChunker] = None,
        embedding_provider: Optional[EmbeddingProvider] = None,
        vector_store: Optional[VectorStore] = None,
        repository: Optional[SQLiteKnowledgeRepository] = None,
        chunk_size: int = 512,
        chunk_overlap: int = 64
    ) -> None:
        self.parser = parser or UnifiedDocumentParser()
        self.chunker = chunker or ConfigurableTextChunker()
        self.embedding_provider = embedding_provider or LocalHashEmbeddingProvider()
        self.repository = repository or SQLiteKnowledgeRepository()
        self.vector_store = vector_store or LocalVectorStore(repository=self.repository)

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def ingest_file(
        self,
        file_path: str,
        chunk_strategy: Optional[ChunkStrategy] = None
    ) -> Document:
        """Ingests, parses, chunks, embeds, and indexes a file path."""
        logger.info(f"Starting ingestion pipeline for file: '{file_path}'...")

        # 1. Parse Document
        doc = self.parser.parse(file_path)

        # 2. Chunk Document
        active_chunker = (
            ConfigurableTextChunker(strategy=chunk_strategy)
            if chunk_strategy
            else self.chunker
        )
        raw_chunks = active_chunker.chunk(
            document=doc,
            chunk_size=self.chunk_size,
            overlap=self.chunk_overlap
        )

        # 3. Generate Vector Embeddings
        chunk_texts = [c.content for c in raw_chunks]
        embeddings = self.embedding_provider.embed_batch(chunk_texts)

        embedded_chunks: List[DocumentChunk] = []
        for chunk, emb in zip(raw_chunks, embeddings):
            ec = DocumentChunk(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                content=chunk.content,
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                embedding=tuple(emb),
                metadata=dict(chunk.metadata)
            )
            embedded_chunks.append(ec)

        # 4. Save Document & Index Chunks
        self.repository.save_document(doc)
        self.vector_store.add_chunks(embedded_chunks)

        logger.info(f"Ingestion pipeline complete for '{doc.title}' ({len(embedded_chunks)} chunks indexed).")
        return doc
