"""Unit tests for GlobalShortcutManager."""

import os
import pytest
from PySide6.QtWidgets import QApplication, QMainWindow

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.gui.shortcuts import GlobalShortcutManager


def test_global_shortcut_binding():
    app = QApplication.instance() or QApplication([])

    win = QMainWindow()
    mgr = GlobalShortcutManager(win)

    called = []
    shortcut = mgr.bind_shortcut("Ctrl+Shift+P", lambda: called.append(True))
    assert shortcut is not None
