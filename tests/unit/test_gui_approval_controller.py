"""Unit tests for ApprovalController."""

import os
import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.gui.approval import ApprovalController


def test_approval_controller_resolution():
    app = QApplication.instance() or QApplication([])

    ctrl = ApprovalController()
    resolutions = []
    ctrl.action_resolved.connect(lambda aid, dec: resolutions.append((aid, dec)))

    ctrl.resolve_action("APPROVE", "act_101")
    if ctrl.active_worker:
        ctrl.active_worker.wait(2000)
    app.processEvents()

    assert len(resolutions) == 1
    assert resolutions[0] == ("act_101", "APPROVE")
