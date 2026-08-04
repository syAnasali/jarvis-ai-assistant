"""MemoryController managing memory record CRUD operations and QThread workers."""

from typing import Any, List, Optional
from PySide6.QtCore import QObject, Signal
from app.core.logger import JarvisLogger
from app.gui.memory.worker import MemoryWorker

logger = JarvisLogger.get_logger("gui_memory_controller")


class MemoryController(QObject):
    """Controller orchestrating Memory Center actions."""

    records_loaded = Signal(list)
    status_updated = Signal(str)

    def __init__(self, memory_manager: Optional[Any] = None, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.memory_manager = memory_manager
        self.active_worker: Optional[MemoryWorker] = None

    def search_memories(self, query: str = "") -> None:
        """Triggers asynchronous memory query worker."""
        if self.active_worker and self.active_worker.isRunning():
            self.active_worker.wait()

        self.active_worker = MemoryWorker(action="search", query=query, memory_manager=self.memory_manager, parent=self)
        self.active_worker.query_completed.connect(self.records_loaded.emit)
        self.active_worker.status_changed.connect(self.status_updated.emit)
        self.active_worker.start()
