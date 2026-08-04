"""KnowledgeSearchWidget hybrid vector + BM25 search bar."""

from typing import Optional
from PySide6.QtWidgets import QLineEdit, QWidget


class KnowledgeSearchWidget(QLineEdit):
    """Hybrid RAG vector + BM25 search bar."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setPlaceholderText("Search Knowledge Base (Hybrid Vector + BM25)...")
        self.setFixedWidth(320)
        self.setStyleSheet("background-color: #1a1d29; border: 1px solid #242838; border-radius: 6px; padding: 4px 8px; color: #e2e8f0;")
