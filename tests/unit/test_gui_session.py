"""Unit tests for SessionRestoreManager."""

import os
import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.gui.session import SessionRestoreManager


def test_session_restore_manager():
    app = QApplication.instance() or QApplication([])

    mgr = SessionRestoreManager(application="TestSessionApp")
    mgr.save_session("knowledge", "draft query")

    assert mgr.restore_active_page() == "knowledge"
    assert mgr.restore_draft_text() == "draft query"
