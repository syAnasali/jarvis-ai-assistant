"""Unit tests for PluginBrowserWidget."""

import os
import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.gui.plugins.browser import PluginBrowserWidget


def test_plugin_browser_widget():
    app = QApplication.instance() or QApplication([])

    browser = PluginBrowserWidget()
    assert len(browser.plugins) >= 3

    selected = []
    browser.plugin_selected.connect(lambda p: selected.append(p))
    browser.selectRow(0)

    assert len(selected) == 1
    assert selected[0]["id"] == "plugin_code"
