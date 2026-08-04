"""Unit tests for PluginsView."""

import os
import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.gui.views.plugins_view import PluginsView


def test_plugins_view_reload():
    app = QApplication.instance() or QApplication([])

    view = PluginsView()
    view.btn_reload_all.click()

    if view.controller.active_worker:
        view.controller.active_worker.wait(2000)
    app.processEvents()

    assert len(view.browser.plugins) >= 3
