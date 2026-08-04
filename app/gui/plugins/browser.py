"""PluginBrowserWidget table presenting installed plugins, health metrics, and lifecycle actions."""

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


class PluginBrowserWidget(QTableWidget):
    """Table view presenting installed plugins, versions, health status, and lifecycle buttons."""

    plugin_selected = Signal(dict)
    action_triggered = Signal(str, str)  # (action, plugin_id)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setColumnCount(7)
        self.setHorizontalHeaderLabels(["Name", "Version", "Author", "Status", "Health", "Startup", "Actions"])
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSelectionMode(QTableWidget.SingleSelection)
        self.setStyleSheet("QTableWidget { background-color: #12141c; color: #e2e8f0; gridline-color: #242838; border: 1px solid #242838; border-radius: 6px; }")

        self.plugins: List[Dict[str, Any]] = [
            {"id": "plugin_code", "name": "Code Interpreter & Execution Sandbox", "version": "1.0.0", "author": "Jarvis Core", "status": "ENABLED", "health": "HEALTHY", "startup": "12 ms", "permissions": ["filesystem", "desktop"], "tools": ["code_eval"], "hooks": ["tool_executor"]},
            {"id": "plugin_rag", "name": "RAG Document Hybrid Indexer", "version": "1.1.2", "author": "Jarvis Core", "status": "ENABLED", "health": "HEALTHY", "startup": "18 ms", "permissions": ["filesystem", "knowledge"], "tools": ["knowledge.ingest"], "hooks": ["knowledge_retriever"]},
            {"id": "plugin_web", "name": "Web Scraping & Search Automation", "version": "0.9.5", "author": "Jarvis Extensions", "status": "DISABLED", "health": "HEALTHY", "startup": "8 ms", "permissions": ["network"], "tools": ["web_search"], "hooks": []},
        ]
        self.populate_table(self.plugins)
        self.itemSelectionChanged.connect(self._on_selection_changed)

    def populate_table(self, records: List[Dict[str, Any]]) -> None:
        """Populates table rows."""
        self.plugins = records
        self.setRowCount(len(records))
        for row, rec in enumerate(records):
            self.setItem(row, 0, QTableWidgetItem(rec.get("name", "")))
            self.setItem(row, 1, QTableWidgetItem(rec.get("version", "1.0.0")))
            self.setItem(row, 2, QTableWidgetItem(rec.get("author", "")))

            status_item = QTableWidgetItem(rec.get("status", "ENABLED"))
            status_item.setForeground(Qt.green if rec.get("status") == "ENABLED" else Qt.gray)
            self.setItem(row, 3, status_item)

            health_item = QTableWidgetItem(rec.get("health", "HEALTHY"))
            health_item.setForeground(Qt.green if rec.get("health") == "HEALTHY" else Qt.red)
            self.setItem(row, 4, health_item)

            self.setItem(row, 5, QTableWidgetItem(rec.get("startup", "10 ms")))

            # Action Buttons Cell
            cell_widget = QWidget()
            btn_layout = QHBoxLayout(cell_widget)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            btn_layout.setSpacing(4)

            is_enabled = rec.get("status") == "ENABLED"
            btn_toggle = QPushButton("Disable" if is_enabled else "Enable")
            btn_toggle.setFixedSize(54, 22)
            pid = rec.get("id", "")
            btn_toggle.clicked.connect(lambda checked=False, p=pid, act="disable" if is_enabled else "enable": self.action_triggered.emit(act, p))
            btn_layout.addWidget(btn_toggle)

            btn_reload = QPushButton("Reload")
            btn_reload.setFixedSize(50, 22)
            btn_reload.clicked.connect(lambda checked=False, p=pid: self.action_triggered.emit("reload", p))
            btn_layout.addWidget(btn_reload)

            self.setCellWidget(row, 6, cell_widget)

    def _on_selection_changed(self) -> None:
        row = self.currentRow()
        if 0 <= row < len(self.plugins):
            self.plugin_selected.emit(self.plugins[row])
