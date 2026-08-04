"""RequestDetailsWidget inspector panel presenting request trace attributes and metrics."""

from typing import Any, Dict, Optional
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import Qt


class RequestDetailsWidget(QFrame):
    """Inspector panel rendering selected request properties and span attributes."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.setStyleSheet("background-color: #1a1d29; border: 1px solid #242838; border-radius: 8px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        lbl_hdr = QLabel("🔍 Request Trace Inspector")
        lbl_hdr.setStyleSheet("font-weight: 600; color: #818cf8; font-size: 12px;")
        layout.addWidget(lbl_hdr)

        self.lbl_id = QLabel("Trace ID: tr_8f91a02b")
        self.lbl_id.setStyleSheet("color: #e2e8f0; font-size: 12px; font-weight: 600;")
        layout.addWidget(self.lbl_id)

        self.lbl_duration = QLabel("Duration: 124 ms")
        self.lbl_duration.setStyleSheet("color: #38bdf8; font-size: 11px;")
        layout.addWidget(self.lbl_duration)

        self.lbl_spans = QLabel("Total Spans: 3 (1 Root, 2 Child Spans)")
        self.lbl_spans.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(self.lbl_spans)

        self.lbl_attrs = QLabel("Attributes: model=llama3, provider=ollama, tokens_generated=68")
        self.lbl_attrs.setWordWrap(True)
        self.lbl_attrs.setStyleSheet("color: #34d399; font-size: 11px;")
        layout.addWidget(self.lbl_attrs)
