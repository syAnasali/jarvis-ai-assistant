"""KnowledgeView assembling IngestionDropZoneWidget, KnowledgeSearchWidget, KnowledgeBrowserWidget, KnowledgeCitationsWidget, and DocumentPreviewWidget."""

from typing import Any, Dict, List, Optional
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt
from app.gui.knowledge.browser import KnowledgeBrowserWidget
from app.gui.knowledge.citations import KnowledgeCitationsWidget
from app.gui.knowledge.controller import KnowledgeController
from app.gui.knowledge.ingestion import IngestionDropZoneWidget
from app.gui.knowledge.preview import DocumentPreviewWidget
from app.gui.knowledge.search import KnowledgeSearchWidget


class KnowledgeView(QWidget):
    """Knowledge Center interface powering Personal Knowledge Base (RAG) document search and ingestion."""

    def __init__(self, knowledge_manager: Optional[Any] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.controller = KnowledgeController(knowledge_manager=knowledge_manager, parent=self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. Header Toolbar
        hdr_layout = QHBoxLayout()
        lbl_title = QLabel("Personal Knowledge Base (RAG)")
        lbl_title.setObjectName("headerTitle")
        hdr_layout.addWidget(lbl_title)
        hdr_layout.addStretch()

        self.search_widget = KnowledgeSearchWidget(self)
        self.search_widget.textChanged.connect(self.controller.search_knowledge)
        hdr_layout.addWidget(self.search_widget)

        layout.addLayout(hdr_layout)

        # 2. Ingestion Drop Zone
        self.drop_zone = IngestionDropZoneWidget(self)
        layout.addWidget(self.drop_zone)

        # 3. Main Splitter (Left: Documents Browser | Right: Match Citations & Content Preview)
        splitter = QSplitter(Qt.Horizontal)

        self.browser = KnowledgeBrowserWidget(self)
        splitter.addWidget(self.browser)

        # Right Column: Match Citations + Previewer
        right_col = QWidget()
        r_layout = QVBoxLayout(right_col)
        r_layout.setContentsMargins(0, 0, 0, 0)
        r_layout.setSpacing(8)

        self.citations_widget = KnowledgeCitationsWidget(self)
        r_layout.addWidget(self.citations_widget)

        self.preview_widget = DocumentPreviewWidget(self)
        r_layout.addWidget(self.preview_widget)

        splitter.addWidget(right_col)

        splitter.setSizes([550, 450])
        layout.addWidget(splitter)

        # Wire Signals
        self.drop_zone.files_dropped.connect(self.controller.ingest_files)
        self.browser.document_selected.connect(self._on_document_selected)
        self.controller.documents_updated.connect(self._on_documents_updated)
        self.controller.search_completed.connect(self.citations_widget.set_results)

    def _on_document_selected(self, doc_dict: Dict[str, Any]) -> None:
        self.preview_widget.set_content(doc_dict.get("content", "No Content"))

    def _on_documents_updated(self, new_docs: List[Dict[str, Any]]) -> None:
        self.browser.documents.extend(new_docs)
        self.browser.populate_table(self.browser.documents)
