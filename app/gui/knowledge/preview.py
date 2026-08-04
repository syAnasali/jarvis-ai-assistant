"""DocumentPreviewWidget multi-format previewer with chunk highlights."""

from typing import Optional
from PySide6.QtWidgets import QFrame, QLabel, QPlainTextEdit, QVBoxLayout, QWidget
from PySide6.QtCore import Qt


class DocumentPreviewWidget(QFrame):
    """Document text previewer supporting chunk text highlighting."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.setStyleSheet("background-color: #1a1d29; border: 1px solid #242838; border-radius: 8px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        lbl_hdr = QLabel("📖 Document Content Preview")
        lbl_hdr.setStyleSheet("font-weight: 600; color: #818cf8; font-size: 12px;")
        layout.addWidget(lbl_hdr)

        self.txt_preview = QPlainTextEdit()
        self.txt_preview.setReadOnly(True)
        self.txt_preview.setPlaceholderText("Select a document or search result to preview content...")
        self.txt_preview.setStyleSheet("background-color: #12141c; color: #e2e8f0; font-family: Consolas; font-size: 11px; border: none;")
        layout.addWidget(self.txt_preview)

    def set_content(self, text: str) -> None:
        """Sets preview text."""
        self.txt_preview.setPlainText(text)
