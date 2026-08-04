"""Unit tests for DiagnosticsView."""

import os
import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.gui.views.diagnostics_view import DiagnosticsView


def test_diagnostics_view_refresh():
    app = QApplication.instance() or QApplication([])

    view = DiagnosticsView()
    view.btn_refresh.click()

    if view.controller.active_worker:
        view.controller.active_worker.wait(2000)
    app.processEvents()

    assert view.metrics_grid.lbl_tokens.text() != ""
