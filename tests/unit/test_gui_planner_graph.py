"""Unit tests for DagGraphWidget."""

import os
import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.gui.planner.graph import DagGraphWidget


def test_dag_graph_widget():
    app = QApplication.instance() or QApplication([])

    graph = DagGraphWidget()
    assert len(graph.nodes) == 4

    graph.update_node_status("node_1", "FAILED")
    assert graph.nodes[0]["status"] == "FAILED"
