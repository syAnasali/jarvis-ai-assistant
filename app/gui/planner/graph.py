"""DagGraphWidget visual DAG node graph renderer and inspector panel."""

from typing import Any, Dict, List, Optional
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Signal, QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QBrush


class DagGraphWidget(QFrame):
    """Visual DAG node dependency graph renderer and click inspector."""

    node_selected = Signal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.setMinimumHeight(240)
        self.setStyleSheet("background-color: #12141c; border: 1px solid #242838; border-radius: 8px;")

        self.nodes: List[Dict[str, Any]] = [
            {"id": "node_1", "name": "Parse Document Context", "status": "COMPLETED", "x": 40, "y": 90, "tool": "knowledge.ingest"},
            {"id": "node_2", "name": "Execute Semantic Search", "status": "COMPLETED", "x": 220, "y": 90, "tool": "knowledge.query"},
            {"id": "node_3", "name": "Synthesize Analysis Plan", "status": "RUNNING", "x": 400, "y": 90, "tool": "planner.synthesize"},
            {"id": "node_4", "name": "Verify Execution Results", "status": "WAITING", "x": 580, "y": 90, "tool": "verifier.eval"},
        ]
        self.selected_node: Optional[Dict[str, Any]] = self.nodes[2]

    def set_dag_nodes(self, nodes_list: List[Dict[str, Any]]) -> None:
        """Updates DAG graph nodes."""
        self.nodes = nodes_list
        self.update()

    def update_node_status(self, node_id: str, status: str) -> None:
        """Updates node status by ID."""
        for n in self.nodes:
            if n.get("id") == node_id:
                n["status"] = status
                break
        self.update()

    def mousePressEvent(self, event: Any) -> None:
        pos = event.pos()
        for node in self.nodes:
            rect = QRect(node["x"], node["y"], 140, 44)
            if rect.contains(pos):
                self.selected_node = node
                self.node_selected.emit(node)
                self.update()
                break

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 1. Draw dependency edges
        pen_edge = QPen(QColor("#475569"), 2, Qt.DashLine)
        painter.setPen(pen_edge)
        for i in range(len(self.nodes) - 1):
            n1 = self.nodes[i]
            n2 = self.nodes[i + 1]
            painter.drawLine(n1["x"] + 140, n1["y"] + 22, n2["x"], n2["y"] + 22)

        # 2. Draw nodes
        for node in self.nodes:
            rect = QRect(node["x"], node["y"], 140, 44)
            status = node.get("status", "WAITING")

            if status == "COMPLETED":
                bg_color = QColor("#065f46")
                border_color = QColor("#10b981")
            elif status == "RUNNING":
                bg_color = QColor("#312e81")
                border_color = QColor("#6366f1")
            elif status == "FAILED":
                bg_color = QColor("#7f1d1d")
                border_color = QColor("#ef4444")
            else:  # WAITING
                bg_color = QColor("#1e293b")
                border_color = QColor("#475569")

            if node == self.selected_node:
                border_color = QColor("#fbbf24")

            painter.setBrush(QBrush(bg_color))
            painter.setPen(QPen(border_color, 2 if node == self.selected_node else 1))
            painter.drawRoundedRect(rect, 6, 6)

            # Node Label
            painter.setPen(QPen(QColor("#ffffff")))
            painter.drawText(rect.adjusted(6, 4, -6, -20), Qt.AlignLeft, node.get("name", ""))

            # Tool Label
            painter.setPen(QPen(QColor("#94a3b8")))
            painter.drawText(rect.adjusted(6, 22, -6, -4), Qt.AlignLeft, f"Tool: {node.get('tool', 'n/a')}")

        painter.end()
