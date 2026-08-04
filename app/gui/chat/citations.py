"""CitationWidget rendering expandable RAG source document references."""

from typing import Any, Dict, Optional
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices


class CitationWidget(QFrame):
    """Expandable RAG Citation card with clickable file:/// references."""

    def __init__(self, citation_dict: Dict[str, Any], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.setStyleSheet("background-color: #181b26; border: 1px solid #242838; border-radius: 6px; padding: 6px;")

        self.title = citation_dict.get("title", "Document Reference")
        self.page = citation_dict.get("page", 1)
        self.file_url = citation_dict.get("url", "")
        self.snippet = citation_dict.get("snippet", "")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)

        lbl_hdr = QLabel(f"📄 Source: {self.title} (Page {self.page})")
        lbl_hdr.setStyleSheet("font-weight: 600; color: #818cf8; font-size: 12px;")
        layout.addWidget(lbl_hdr)

        if self.snippet:
            lbl_snip = QLabel(f'"{self.snippet}"')
            lbl_snip.setWordWrap(True)
            lbl_snip.setStyleSheet("color: #94a3b8; font-style: italic; font-size: 11px;")
            layout.addWidget(lbl_snip)

        if self.file_url:
            lbl_link = QLabel(f'<a href="{self.file_url}">Open Local File ({self.file_url})</a>')
            lbl_link.setOpenExternalLinks(True)
            lbl_link.setStyleSheet("color: #6366f1; font-size: 11px;")
            layout.addWidget(lbl_link)
