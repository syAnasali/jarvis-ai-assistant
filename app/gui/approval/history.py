"""ApprovalHistoryWidget log table recording approved and rejected tool requests."""

from typing import Any, Dict, List, Optional
from PySide6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem, QWidget
from PySide6.QtCore import Qt


class ApprovalHistoryWidget(QTableWidget):
    """Table view displaying historical tool approval decisions and execution statuses."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels(["ID", "Tool", "Decision", "Duration", "Timestamp"])
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.setStyleSheet("QTableWidget { background-color: #12141c; color: #e2e8f0; gridline-color: #242838; border: 1px solid #242838; border-radius: 6px; }")

        self.history: List[Dict[str, Any]] = [
            {"id": "app_01", "tool_name": "python_eval", "decision": "APPROVED", "duration": "45 ms", "timestamp": "10:14:02"},
            {"id": "app_02", "tool_name": "system.execute_cmd", "decision": "REJECTED", "duration": "0 ms", "timestamp": "10:14:15"},
        ]
        self.populate_table(self.history)

    def populate_table(self, records: List[Dict[str, Any]]) -> None:
        """Populates history table rows."""
        self.history = records
        self.setRowCount(len(records))
        for row, rec in enumerate(records):
            self.setItem(row, 0, QTableWidgetItem(rec.get("id", "")))
            self.setItem(row, 1, QTableWidgetItem(rec.get("tool_name", "")))

            dec_item = QTableWidgetItem(rec.get("decision", "APPROVED"))
            dec_item.setForeground(Qt.green if rec.get("decision") == "APPROVED" else Qt.red)
            self.setItem(row, 2, dec_item)

            self.setItem(row, 3, QTableWidgetItem(rec.get("duration", "0 ms")))
            self.setItem(row, 4, QTableWidgetItem(rec.get("timestamp", "")))
