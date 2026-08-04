"""IngestionDropZoneWidget drag & drop target for Knowledge Base file ingestion."""

from pathlib import Path
from typing import Any, List, Optional
from PySide6.QtWidgets import QFileDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget
from PySide6.QtCore import Signal, Qt


class IngestionDropZoneWidget(QFrame):
    """Drag & drop target and file picker for document ingestion into RAG knowledge base."""

    files_dropped = Signal(list)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.setAcceptDrops(True)
        self.setStyleSheet("""
            QFrame#cardFrame {
                background-color: #181b26;
                border: 2px dashed #475569;
                border-radius: 8px;
                padding: 12px;
            }
            QFrame#cardFrame:hover {
                border-color: #6366f1;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(6)

        lbl = QLabel("📂 Drag & Drop Documents or Folders Here")
        lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #818cf8;")
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl)

        lbl_sub = QLabel("Supports PDF, Markdown, TXT, DOCX, HTML, and Code files")
        lbl_sub.setStyleSheet("font-size: 11px; color: #94a3b8;")
        lbl_sub.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_sub)

        self.btn_browse = QPushButton("Browse Files...")
        self.btn_browse.setFixedWidth(120)
        self.btn_browse.clicked.connect(self._browse_files)
        layout.addWidget(self.btn_browse, alignment=Qt.AlignCenter)

    def _browse_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Select Documents to Ingest", "", "All Documents (*.pdf *.md *.txt *.docx *.html *.py *.json)")
        if files:
            self.files_dropped.emit(files)

    def dragEnterEvent(self, event: Any) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: Any) -> None:
        urls = event.mimeData().urls()
        files = [u.toLocalFile() for u in urls if u.isLocalFile()]
        if files:
            self.files_dropped.emit(files)
