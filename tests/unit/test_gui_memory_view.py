"""Unit tests for MemoryView."""

import os
import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.gui.views.memory_view import MemoryView


def test_memory_view_interaction():
    app = QApplication.instance() or QApplication([])

    view = MemoryView()
    view.search_widget.setText("PySide6")

    if view.controller.active_worker:
        view.controller.active_worker.wait(2000)
    app.processEvents()

    assert len(view.browser.memories) > 0
