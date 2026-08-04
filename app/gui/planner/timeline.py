"""ExecutionTimelineWidget displaying chronological step events for plan execution."""

from typing import Dict, List, Optional
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget, QScrollArea
from PySide6.QtCore import Qt


class ExecutionTimelineWidget(QFrame):
    """Chronological execution timeline list presenting step transitions."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.setStyleSheet("background-color: #1a1d29; border: 1px solid #242838; border-radius: 8px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        lbl_title = QLabel("⏱️ Chronological Execution Timeline")
        lbl_title.setStyleSheet("font-weight: 600; color: #818cf8; font-size: 12px;")
        layout.addWidget(lbl_title)

        # Scrollable Timeline Area
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

    def add_timeline_event(self, step_type: str, title: str, timestamp: str = "Just now") -> None:
        """Adds a step event card to the timeline."""
        badge = QLabel(f"• [{step_type.upper()}] {title} ({timestamp})")
        badge.setWordWrap(True)

        if step_type.lower() == "planning":
            badge.setStyleSheet("color: #818cf8; font-size: 11px;")
        elif step_type.lower() == "tool":
            badge.setStyleSheet("color: #38bdf8; font-size: 11px;")
        elif step_type.lower() == "verification":
            badge.setStyleSheet("color: #34d399; font-size: 11px;")
        elif step_type.lower() == "recovery":
            badge.setStyleSheet("color: #fbbf24; font-size: 11px;")
        else:
            badge.setStyleSheet("color: #10b981; font-size: 11px; font-weight: 600;")

        self.c_layout.insertWidget(self.c_layout.count() - 1, badge)

    def clear(self) -> None:
        """Clears timeline events."""
        while self.c_layout.count() > 1:
            item = self.c_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
