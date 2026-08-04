"""LiveExecutionLogsWidget streaming real-time logs with search and filter controls."""

from typing import Optional
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt


class LiveExecutionLogsWidget(QFrame):
    """Live execution log stream with search filter and export controls."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.setStyleSheet("background-color: #1a1d29; border: 1px solid #242838; border-radius: 8px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # Header & Filter Toolbar
        hdr_row = QHBoxLayout()
        lbl_hdr = QLabel("📜 Live Execution Logs")
        lbl_hdr.setStyleSheet("font-weight: 600; color: #818cf8; font-size: 12px;")
        hdr_row.addWidget(lbl_hdr)
        hdr_row.addStretch()

        self.txt_filter = QLineEdit()
        self.txt_filter.setPlaceholderText("Filter logs...")
        self.txt_filter.setFixedWidth(140)
        hdr_row.addWidget(self.txt_filter)

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setFixedSize(50, 22)
        self.btn_clear.clicked.connect(self.clear_logs)
        hdr_row.addWidget(self.btn_clear)

        layout.addLayout(hdr_row)

        # Log Text Area
        self.txt_logs = QPlainTextEdit()
        self.txt_logs.setReadOnly(True)
        self.txt_logs.setStyleSheet("background-color: #12141c; color: #94a3b8; font-family: Consolas; font-size: 11px; border: none;")
        layout.addWidget(self.txt_logs)

    def append_log(self, log_line: str) -> None:
        """Appends log line to live log view."""
        self.txt_logs.appendPlainText(log_line)

    def clear_logs(self) -> None:
        """Clears log panel."""
        self.txt_logs.clear()
