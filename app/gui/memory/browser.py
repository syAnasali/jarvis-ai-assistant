"""MemoryBrowserWidget table displaying memory records and facts."""

from typing import Any, Dict, List, Optional
from PySide6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem, QWidget
from PySide6.QtCore import Signal, Qt


class MemoryBrowserWidget(QTableWidget):
    """Table view displaying memory facts, preferences, projects, and context records."""

    memory_selected = Signal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels(["ID", "Type", "Content", "Importance", "Created"])
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSelectionMode(QTableWidget.SingleSelection)
        self.setStyleSheet("QTableWidget { background-color: #12141c; color: #e2e8f0; gridline-color: #242838; border: 1px solid #242838; border-radius: 6px; }")

        self.memories: List[Dict[str, Any]] = [
            {"id": "mem_01", "type": "Preference", "content": "User prefers dark mode UI styling and Python 3.13", "importance": "High", "source": "User Settings", "created_at": "2026-08-04"},
            {"id": "mem_02", "type": "Fact", "content": "Jarvis uses PySide6 for Desktop GUI and Loguru for logging", "importance": "High", "source": "Code Base", "created_at": "2026-08-04"},
            {"id": "mem_03", "type": "Project", "content": "Phase 25.5 Memory & Knowledge Center for PySide6 GUI", "importance": "Medium", "source": "Roadmap", "created_at": "2026-08-05"},
            {"id": "mem_04", "type": "Context", "content": "SQLite databases stored in data/jarvis.db with retention policy", "importance": "Medium", "source": "System Config", "created_at": "2026-08-05"},
        ]
        self.populate_table(self.memories)
        self.itemSelectionChanged.connect(self._on_selection_changed)

    def populate_table(self, records: List[Dict[str, Any]]) -> None:
        """Populates table rows."""
        self.memories = records
        self.setRowCount(len(records))
        for row, rec in enumerate(records):
            self.setItem(row, 0, QTableWidgetItem(rec.get("id", "")))
            self.setItem(row, 1, QTableWidgetItem(rec.get("type", "Fact")))
            self.setItem(row, 2, QTableWidgetItem(rec.get("content", "")))
            self.setItem(row, 3, QTableWidgetItem(rec.get("importance", "High")))
            self.setItem(row, 4, QTableWidgetItem(rec.get("created_at", "")))

    def _on_selection_changed(self) -> None:
        row = self.currentRow()
        if 0 <= row < len(self.memories):
            self.memory_selected.emit(self.memories[row])
