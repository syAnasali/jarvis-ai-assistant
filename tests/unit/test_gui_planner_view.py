"""Unit tests for PlannerView."""

import os
import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.gui.views.planner_view import PlannerView


def test_planner_view_execution():
    app = QApplication.instance() or QApplication([])

    view = PlannerView()
    view.btn_execute.click()

    if view.controller.active_worker:
        view.controller.active_worker.wait(3000)
    app.processEvents()

    assert view.progress_tracker.progress_bar.value() == 100
