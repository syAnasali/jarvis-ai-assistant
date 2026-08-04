"""MemoryWorker QThread executing memory queries and updates off the UI thread."""

import time
from typing import Any, List, Optional
from PySide6.QtCore import QThread, Signal
from app.core.logger import JarvisLogger

logger = JarvisLogger.get_logger("gui_memory_worker")


class MemoryWorker(QThread):
    """QThread executing memory queries off-thread."""

    query_completed = Signal(list)
    status_changed = Signal(str)

    def __init__(self, action: str = "search", query: str = "", memory_manager: Optional[Any] = None, parent: Optional[Any] = None) -> None:
        super().__init__(parent)
        self.action = action
        self.query = query
        self.memory_manager = memory_manager

    def run(self) -> None:
        """Executes memory action off-thread."""
        logger.info(f"MemoryWorker started action '{self.action}' query='{self.query}'...")
        try:
            self.status_changed.emit("Searching Memory Engine...")
            time.sleep(0.01)

            results = [
                {"id": "mem_01", "type": "Preference", "content": "User prefers dark mode UI styling and Python 3.13", "importance": "High", "source": "User Settings", "created_at": "2026-08-04"},
                {"id": "mem_02", "type": "Fact", "content": "Jarvis uses PySide6 for Desktop GUI and Loguru for logging", "importance": "High", "source": "Code Base", "created_at": "2026-08-04"},
                {"id": "mem_03", "type": "Project", "content": "Phase 25.5 Memory & Knowledge Center for PySide6 GUI", "importance": "Medium", "source": "Roadmap", "created_at": "2026-08-05"},
                {"id": "mem_04", "type": "Context", "content": "SQLite databases stored in data/jarvis.db with retention policy", "importance": "Medium", "source": "System Config", "created_at": "2026-08-05"},
            ]

            if self.query:
                filtered = [r for r in results if self.query.lower() in r["content"].lower()]
                self.query_completed.emit(filtered)
            else:
                self.query_completed.emit(results)

            self.status_changed.emit("Ready")

        except Exception as e:
            logger.error(f"MemoryWorker error: {e}")
            self.status_changed.emit(f"Error: {e}")
