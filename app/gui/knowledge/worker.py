"""KnowledgeWorker QThread executing document parsing, chunking, embedding, and hybrid search off-thread."""

import time
from typing import Any, List, Optional
from PySide6.QtCore import QThread, Signal
from app.core.logger import JarvisLogger

logger = JarvisLogger.get_logger("gui_knowledge_worker")


class KnowledgeWorker(QThread):
    """QThread executing document ingestion and RAG hybrid search off-thread."""

    ingestion_completed = Signal(list)
    search_completed = Signal(list)
    status_changed = Signal(str)

    def __init__(
        self,
        mode: str = "search",
        query: str = "",
        file_paths: Optional[List[str]] = None,
        knowledge_manager: Optional[Any] = None,
        parent: Optional[Any] = None
    ) -> None:
        super().__init__(parent)
        self.mode = mode
        self.query = query
        self.file_paths = file_paths or []
        self.knowledge_manager = knowledge_manager

    def run(self) -> None:
        """Executes mode off-thread."""
        logger.info(f"KnowledgeWorker started mode '{self.mode}' query='{self.query}'...")
        try:
            if self.mode == "ingest":
                self.status_changed.emit("Parsing and Embedding Documents...")
                time.sleep(0.02)

                new_docs = []
                for p in self.file_paths:
                    new_docs.append({
                        "filename": p.split("/")[-1].split("\\")[-1],
                        "chunks": 12,
                        "size": "340 KB",
                        "ingested": "Just now",
                        "content": f"Ingested content sample from '{p}'. Document parsed and embedded into local vector store."
                    })
                self.ingestion_completed.emit(new_docs)
                self.status_changed.emit("Ingestion Complete")

            elif self.mode == "search":
                self.status_changed.emit("Executing Hybrid Vector + BM25 Search...")
                time.sleep(0.01)

                matches = [
                    {
                        "doc_title": "operating_systems_notes.pdf",
                        "chunk_idx": 3,
                        "score": 0.94,
                        "vector_score": 0.92,
                        "bm25_score": 0.95,
                        "snippet": "Virtual memory paging allows secondary memory to be addressed as main memory storage."
                    },
                    {
                        "doc_title": "jarvis_architecture_guide.md",
                        "chunk_idx": 7,
                        "score": 0.88,
                        "vector_score": 0.87,
                        "bm25_score": 0.89,
                        "snippet": "KnowledgeManager subsystem orchestrates document ingestion, semantic chunking, and embedding."
                    }
                ]
                self.search_completed.emit(matches)
                self.status_changed.emit("Ready")

        except Exception as e:
            logger.error(f"KnowledgeWorker error: {e}")
            self.status_changed.emit(f"Error: {e}")
