"""Unit tests for JarvisGuiApplication and MainWindow components."""

import os
import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.gui.app import JarvisGuiApplication


def test_gui_application_bootstrap():
    gui_app = JarvisGuiApplication()
    assert gui_app.main_window is not None
    assert gui_app.app is not None
