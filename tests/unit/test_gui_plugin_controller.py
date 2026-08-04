"""Unit tests for PluginController."""

import os
import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.gui.plugins.controller import PluginController


def test_plugin_controller_enable():
    app = QApplication.instance() or QApplication([])

    ctrl = PluginController()
    status_updates = []
    ctrl.plugin_status_changed.connect(lambda pid, stat: status_updates.append((pid, stat)))

    ctrl.execute_plugin_action("enable", "plugin_test")
    if ctrl.active_worker:
        ctrl.active_worker.wait(2000)
    app.processEvents()

    assert len(status_updates) == 1
    assert status_updates[0] == ("plugin_test", "ENABLED")
