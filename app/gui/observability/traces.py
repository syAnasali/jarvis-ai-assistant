"""TraceTreeWidget presenting distributed trace trees and parent/child span durations."""

from typing import Any, Dict, List, Optional
from PySide6.QtWidgets import QHeaderView, QTreeWidget, QTreeWidgetItem, QWidget
from PySide6.QtCore import Qt


class TraceTreeWidget(QTreeWidget):
    """Tree view presenting request trace spans, durations, and execution statuses."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setColumnCount(4)
        self.setHeaderLabels(["Span / Operation", "Trace ID", "Duration", "Status"])
        self.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.setStyleSheet("QTreeWidget { background-color: #12141c; color: #e2e8f0; border: 1px solid #242838; border-radius: 6px; }")
        self.populate_sample_traces()


    def populate_sample_traces(self) -> None:
        """Populates trace tree."""
        self.clear()

        # Root Trace Span 1
        root1 = QTreeWidgetItem(["agent.run_step", "tr_8f91a02b", "124 ms", "OK"])
        child1_1 = QTreeWidgetItem(["llm.generate_stream", "span_01", "86 ms", "OK"])
        child1_2 = QTreeWidgetItem(["tool.knowledge.query", "span_02", "32 ms", "OK"])
        root1.addChild(child1_1)
        root1.addChild(child1_2)

        # Root Trace Span 2
        root2 = QTreeWidgetItem(["planner.execute_dag", "tr_7e20b11c", "410 ms", "OK"])
        child2_1 = QTreeWidgetItem(["dag.node_1_parse", "span_03", "140 ms", "OK"])
        child2_2 = QTreeWidgetItem(["dag.node_2_search", "span_04", "260 ms", "OK"])
        root2.addChild(child2_1)
        root2.addChild(child2_2)

        self.addTopLevelItem(root1)
        self.addTopLevelItem(root2)
        self.expandAll()
