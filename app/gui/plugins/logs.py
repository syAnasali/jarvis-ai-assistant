"""PluginLogsWidget displaying real-time plugin lifecycle execution logs."""

from typing import Optional
from PySide6.QtWidgets import QFrame, QLabel, QPlainTextEdit, QVBoxLayout, QWidget
from PySide6.QtCore import Qt


class PluginLogsWidget(QFrame):
    """Live log panel presenting plugin lifecycle events and health check traces."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.setStyleSheet("background-color: #1a1d29; border: 1px solid #242838; border-radius: 8px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        lbl_hdr = QLabel("📜 Plugin Lifecycle Logs")
        lbl_hdr.setStyleSheet("font-weight: 600; color: #818cf8; font-size: 12px;")
        layout.addWidget(lbl_hdr)

        self.txt_logs = QPlainTextEdit()
        self.txt_logs.setReadOnly(True)
        self.txt_logs.setStyleSheet("background-color: #12141c; color: #94a3b8; font-family: Consolas; font-size: 11px; border: none;")
        layout.addWidget(self.txt_logs)

    def append_log(self, text: str) -> None:
        """Appends log line."""
        self.txt_logs.appendPlainText(text)
