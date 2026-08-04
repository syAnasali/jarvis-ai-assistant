"""KnowledgeController managing document ingestion, hybrid search, and QThread workers."""

from typing import Any, List, Optional
from PySide6.QtCore import QObject, Signal
from app.core.logger import JarvisLogger
from app.gui.knowledge.worker import KnowledgeWorker

logger = JarvisLogger.get_logger("gui_knowledge_controller")


class KnowledgeController(QObject):
    """Controller orchestrating Knowledge Base RAG actions."""

    documents_updated = Signal(list)
    search_completed = Signal(list)
    status_updated = Signal(str)

    def __init__(self, knowledge_manager: Optional[Any] = None, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.knowledge_manager = knowledge_manager
        self.active_worker: Optional[KnowledgeWorker] = None

    def ingest_files(self, file_paths: List[str]) -> None:
        """Triggers asynchronous document ingestion worker."""
        if self.active_worker and self.active_worker.isRunning():
            self.active_worker.wait()

        self.active_worker = KnowledgeWorker(mode="ingest", file_paths=file_paths, knowledge_manager=self.knowledge_manager, parent=self)
        self.active_worker.ingestion_completed.connect(self.documents_updated.emit)
        self.active_worker.status_changed.connect(self.status_updated.emit)
        self.active_worker.start()

    def search_knowledge(self, query: str = "") -> None:
        """Triggers asynchronous RAG hybrid search worker."""
        if self.active_worker and self.active_worker.isRunning():
            self.active_worker.wait()

        self.active_worker = KnowledgeWorker(mode="search", query=query, knowledge_manager=self.knowledge_manager, parent=self)
        self.active_worker.search_completed.connect(self.search_completed.emit)
        self.active_worker.status_changed.connect(self.status_updated.emit)
        self.active_worker.start()
