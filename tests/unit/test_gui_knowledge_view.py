"""Unit tests for KnowledgeView."""

import os
import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.gui.views.knowledge_view import KnowledgeView


def test_knowledge_view_search():
    app = QApplication.instance() or QApplication([])

    view = KnowledgeView()
    view.search_widget.setText("vector search")

    if view.controller.active_worker:
        view.controller.active_worker.wait(2000)
    app.processEvents()

    assert len(view.browser.documents) > 0
