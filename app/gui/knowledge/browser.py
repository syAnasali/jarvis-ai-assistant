"""KnowledgeBrowserWidget table displaying indexed documents and chunks."""

from typing import Any, Dict, List, Optional
from PySide6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem, QWidget
from PySide6.QtCore import Signal, Qt


class KnowledgeBrowserWidget(QTableWidget):
    """Table view displaying indexed RAG documents and chunk counts."""

    document_selected = Signal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["Filename", "Chunks", "Size", "Ingested"])
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSelectionMode(QTableWidget.SingleSelection)
        self.setStyleSheet("QTableWidget { background-color: #12141c; color: #e2e8f0; gridline-color: #242838; border: 1px solid #242838; border-radius: 6px; }")

        self.documents: List[Dict[str, Any]] = [
            {"filename": "operating_systems_notes.pdf", "chunks": 14, "size": "1.2 MB", "ingested": "2026-08-04", "content": "Operating Systems Notes: Page Tables, Virtual Memory, CPU Scheduling algorithms, process synchronization semaphores."},
            {"filename": "jarvis_architecture_guide.md", "chunks": 28, "size": "450 KB", "ingested": "2026-08-04", "content": "Jarvis Subsystem Architecture Guide: AgentRunner, MemoryManager, KnowledgeManager, PySide6 GUI layer."},
            {"filename": "python_asyncio_best_practices.txt", "chunks": 8, "size": "120 KB", "ingested": "2026-08-05", "content": "Python Asyncio Best Practices: Event Loop, Task Cancellation, ThreadPoolExecutor integration."},
        ]
        self.populate_table(self.documents)
        self.itemSelectionChanged.connect(self._on_selection_changed)

    def populate_table(self, docs: List[Dict[str, Any]]) -> None:
        """Populates table rows."""
        self.documents = docs
        self.setRowCount(len(docs))
        for row, doc in enumerate(docs):
            self.setItem(row, 0, QTableWidgetItem(doc.get("filename", "")))
            self.setItem(row, 1, QTableWidgetItem(str(doc.get("chunks", 1))))
            self.setItem(row, 2, QTableWidgetItem(doc.get("size", "0 KB")))
            self.setItem(row, 3, QTableWidgetItem(doc.get("ingested", "")))

    def _on_selection_changed(self) -> None:
        row = self.currentRow()
        if 0 <= row < len(self.documents):
            self.document_selected.emit(self.documents[row])
