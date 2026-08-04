"""KnowledgeCitationsWidget rendering hybrid search score breakdowns and snippets."""

from typing import Any, Dict, List, Optional
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget, QScrollArea
from PySide6.QtCore import Qt


class KnowledgeCitationsWidget(QFrame):
    """RAG Hybrid search match card displaying score breakdowns (BM25, Vector, Reranked)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.setStyleSheet("background-color: #1a1d29; border: 1px solid #242838; border-radius: 8px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        lbl_hdr = QLabel("🎯 Top Hybrid RAG Match Results")
        lbl_hdr.setStyleSheet("font-weight: 600; color: #818cf8; font-size: 12px;")
        layout.addWidget(lbl_hdr)

        # Scroll Area for Matches
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        self.container = QWidget()
        self.c_layout = QVBoxLayout(self.container)
        self.c_layout.setContentsMargins(0, 0, 0, 0)
        self.c_layout.setSpacing(6)
        self.c_layout.addStretch()

        scroll.setWidget(self.container)
        layout.addWidget(scroll)

    def set_results(self, matches: List[Dict[str, Any]]) -> None:
        """Populates search match cards."""
        self.clear()
        for m in matches:
            card = QFrame()
            card.setStyleSheet("background-color: #181b26; border: 1px solid #242838; border-radius: 6px; padding: 6px;")
            l = QVBoxLayout(card)
            l.setContentsMargins(6, 6, 6, 6)
            l.setSpacing(2)

            t = QLabel(f"📄 {m.get('doc_title', 'Doc')} (Chunk #{m.get('chunk_idx', 1)})")
            t.setStyleSheet("font-weight: 600; color: #818cf8; font-size: 11px;")
            l.addWidget(t)

            scores = f"Score: {m.get('score', 0.92):.2f} (Vector: {m.get('vector_score', 0.90):.2f} | BM25: {m.get('bm25_score', 0.88):.2f})"
            lbl_s = QLabel(scores)
            lbl_s.setStyleSheet("color: #34d399; font-size: 10px;")
            l.addWidget(lbl_s)

            snip = QLabel(f'"{m.get("snippet", "")}"')
            snip.setWordWrap(True)
            snip.setStyleSheet("color: #e2e8f0; font-size: 11px; font-style: italic;")
            l.addWidget(snip)

            self.c_layout.insertWidget(self.c_layout.count() - 1, card)

    def clear(self) -> None:
        """Clears results."""
        while self.c_layout.count() > 1:
            item = self.c_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
