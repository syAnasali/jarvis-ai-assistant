"""Unit tests for NavigationManager and MainWindow navigation stack."""

import os
import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.gui.main_window import MainWindow


def test_gui_navigation_stack():
    app = QApplication.instance() or QApplication([])

    window = MainWindow()

    pages = ["chat", "planner", "memory", "knowledge", "vision", "voice", "plugins", "diagnostics", "settings"]
    for p in pages:
        assert window.nav_mgr.navigate_to(p) is True
        assert window.nav_mgr.get_active_page() == p
