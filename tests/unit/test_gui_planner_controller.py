"""Unit tests for PlannerController."""

import os
import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.gui.planner.controller import PlannerController


def test_planner_controller():
    app = QApplication.instance() or QApplication([])

    ctrl = PlannerController()
    finished_plans = []
    ctrl.plan_finished.connect(lambda pid: finished_plans.append(pid))

    ctrl.execute_plan("plan_test")
    if ctrl.active_worker:
        ctrl.active_worker.wait(3000)
    app.processEvents()

    assert len(finished_plans) == 1
    assert finished_plans[0] == "plan_test"
