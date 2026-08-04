"""ApprovalQueueWidget table presenting pending tool approval requests."""

from typing import Any, Dict, List, Optional
from PySide6.QtWidgets import (
    QHeaderView,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)
from PySide6.QtCore import Signal, Qt


class ApprovalQueueWidget(QTableWidget):
    """Table view presenting pending tool action approval requests."""

    action_selected = Signal(dict)
    resolve_requested = Signal(str, str)  # (decision, action_id)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels(["ID", "Tool", "Risk Level", "Timestamp", "Actions"])
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSelectionMode(QTableWidget.SingleSelection)
        self.setStyleSheet("QTableWidget { background-color: #12141c; color: #e2e8f0; gridline-color: #242838; border: 1px solid #242838; border-radius: 6px; }")

        self.pending_actions: List[Dict[str, Any]] = [
            {"id": "act_101", "tool_name": "file_writer", "risk_level": "RESTRICTED", "source": "Planner Node #2", "arguments": {"path": "config/settings.json", "content": "{}"}, "timestamp": "10:15:30"},
            {"id": "act_102", "tool_name": "python_eval", "risk_level": "CONFIRMATION", "source": "User Chat", "arguments": {"script": "print('Hello Jarvis')"}, "timestamp": "10:15:42"},
        ]
        self.populate_table(self.pending_actions)
        self.itemSelectionChanged.connect(self._on_selection_changed)

    def populate_table(self, records: List[Dict[str, Any]]) -> None:
        """Populates queue table rows."""
        self.pending_actions = records
        self.setRowCount(len(records))
        for row, rec in enumerate(records):
            self.setItem(row, 0, QTableWidgetItem(rec.get("id", "")))
            self.setItem(row, 1, QTableWidgetItem(rec.get("tool_name", "")))
            self.setItem(row, 2, QTableWidgetItem(rec.get("risk_level", "CONFIRMATION")))
            self.setItem(row, 3, QTableWidgetItem(rec.get("timestamp", "")))

            cell_widget = QWidget()
            btn_layout = QHBoxLayout(cell_widget)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            btn_layout.setSpacing(4)

            aid = rec.get("id", "")
            btn_approve = QPushButton("Approve")
            btn_approve.setFixedSize(56, 22)
            btn_approve.setStyleSheet("background-color: #065f46; color: #34d399; font-weight: 600;")
            btn_approve.clicked.connect(lambda checked=False, a=aid: self.resolve_requested.emit("APPROVE", a))
            btn_layout.addWidget(btn_approve)

            btn_reject = QPushButton("Reject")
            btn_reject.setFixedSize(50, 22)
            btn_reject.setStyleSheet("background-color: #450a0a; color: #f87171; font-weight: 600;")
            btn_reject.clicked.connect(lambda checked=False, a=aid: self.resolve_requested.emit("REJECT", a))
            btn_layout.addWidget(btn_reject)

            self.setCellWidget(row, 4, cell_widget)

    def _on_selection_changed(self) -> None:
        row = self.currentRow()
        if 0 <= row < len(self.pending_actions):
            self.action_selected.emit(self.pending_actions[row])
