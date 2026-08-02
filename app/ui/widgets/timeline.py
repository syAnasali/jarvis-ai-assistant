"""Timeline widget for tracking Jarvis agent steps and actions."""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QScrollArea, QHBoxLayout
from PySide6.QtCore import Qt
from app.ui.theme import BORDER_COLOR, BG_CARD, TEXT_PRIMARY, TEXT_SECONDARY, ACCENT_BLUE, ACCENT_GREEN, ACCENT_AMBER


class TimelineItem(QFrame):
    """Single item in the execution activity timeline."""

    def __init__(self, event_name: str, details: str, timestamp_str: str, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER_COLOR};
                border-radius: 6px;
                padding: 6px;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        
        # Icon / tag color based on event type
        tag_color = ACCENT_BLUE
        if event_name in ("APPROVED", "TOOL_EXECUTED", "COMPLETED"):
            tag_color = ACCENT_GREEN
        elif event_name in ("APPROVAL_REQUESTED", "REJECTED"):
            tag_color = ACCENT_AMBER
        elif event_name == "ERROR":
            tag_color = "#ef476f"  # Accent red
            
        self.icon_lbl = QLabel("●")
        self.icon_lbl.setStyleSheet(f"color: {tag_color}; font-size: 14px; font-weight: bold;")
        layout.addWidget(self.icon_lbl)
        
        # Texts layout
        v_layout = QVBoxLayout()
        v_layout.setSpacing(2)
        v_layout.setContentsMargins(0, 0, 0, 0)
        
        # Header (Event Name + Timestamp)
        h_layout = QHBoxLayout()
        h_layout.setSpacing(10)
        
        name_lbl = QLabel(event_name.replace("_", " "))
        name_lbl.setStyleSheet("font-weight: bold; font-size: 11px;")
        h_layout.addWidget(name_lbl)
        
        # Parse timestamp to a short time
        time_part = timestamp_str
        if "T" in timestamp_str:
            time_part = timestamp_str.split("T")[1].split(".")[0]
            
        time_lbl = QLabel(time_part)
        time_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10px;")
        h_layout.addWidget(time_lbl)
        h_layout.addStretch()
        v_layout.addLayout(h_layout)
        
        # Details label
        det_lbl = QLabel(details)
        det_lbl.setWordWrap(True)
        det_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        v_layout.addWidget(det_lbl)
        
        layout.addLayout(v_layout)


class TimelineWidget(QScrollArea):
    """Scrollable list of timeline events representing the execution track."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.setStyleSheet(f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
        """)
        
        self.container = QFrame()
        self.container.setStyleSheet("background-color: transparent;")
        
        self.scroll_layout = QVBoxLayout(self.container)
        self.scroll_layout.setContentsMargins(5, 5, 5, 5)
        self.scroll_layout.setSpacing(8)
        self.scroll_layout.addStretch()
        
        self.setWidget(self.container)
        self.items = []

    def add_event(self, event_name: str, details: str, timestamp_str: str) -> None:
        """Appends a new event block to the timeline."""
        # Remove spacer at the bottom temporarily, insert item, then re-add spacer
        self.scroll_layout.removeItem(self.scroll_layout.itemAt(self.scroll_layout.count() - 1))
        
        item = TimelineItem(event_name, details, timestamp_str)
        self.scroll_layout.addWidget(item)
        self.items.append(item)
        
        self.scroll_layout.addStretch()
        
        # Scroll to bottom
        from PySide6.QtCore import QTimer
        QTimer.singleShot(50, self._do_scroll)

    def clear(self) -> None:
        """Removes all timeline entries."""
        for item in self.items:
            self.scroll_layout.removeWidget(item)
            item.deleteLater()
        self.items.clear()

    def _do_scroll(self) -> None:
        bar = self.verticalScrollBar()
        bar.setValue(bar.maxValue())
