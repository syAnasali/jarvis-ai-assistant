"""Unit tests for expanded SettingsView."""

import os
import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.gui.views.settings_view import SettingsView


def test_expanded_settings_view():
    app = QApplication.instance() or QApplication([])

    view = SettingsView()
    assert view.tabs.count() == 5
    assert view.spin_font.value() == 11
