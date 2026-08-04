"""TimelineViewWidget presenting chronological request event timelines."""

from typing import Dict, List, Optional
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget, QScrollArea
from PySide6.QtCore import Qt


class TimelineViewWidget(QFrame):
    """Chronological event timeline presenting request lifecycle events across subsystems."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.setStyleSheet("background-color: #1a1d29; border: 1px solid #242838; border-radius: 8px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        lbl_hdr = QLabel("⏱️ Chronological Request Event Timeline")
        lbl_hdr.setStyleSheet("font-weight: 600; color: #818cf8; font-size: 12px;")
        layout.addWidget(lbl_hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        self.container = QWidget()
        self.c_layout = QVBoxLayout(self.container)
        self.c_layout.setContentsMargins(0, 0, 0, 0)
        self.c_layout.setSpacing(4)
        self.c_layout.addStretch()

        scroll.setWidget(self.container)
        layout.addWidget(scroll)

        self.populate_sample_events()

    def populate_sample_events(self) -> None:
        """Populates sample timeline events."""
        events = [
            ("Planning", "Synthesized 4-node DAG graph for document analysis", "10:12:01"),
            ("Knowledge", "Retrieved 3 chunks from operating_systems_notes.pdf (latency=14ms)", "10:12:02"),
            ("Tool", "Executed python_eval sandbox script for data processing", "10:12:03"),
            ("Memory Write", "Validated and persisted fact to SQLite store", "10:12:04"),
            ("Completion", "Streamed response completed successfully", "10:12:05"),
        ]
        for sub, title, ts in events:
            badge = QLabel(f"• [{sub.upper()}] {title} ({ts})")
            badge.setWordWrap(True)
            badge.setStyleSheet("color: #e2e8f0; font-size: 11px;")
            self.c_layout.insertWidget(self.c_layout.count() - 1, badge)
