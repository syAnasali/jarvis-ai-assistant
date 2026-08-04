"""Unit tests for ApprovalDialog."""

import os
import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.gui.approval import ApprovalDialog


def test_approval_dialog():
    app = QApplication.instance() or QApplication([])

    dialog = ApprovalDialog({
        "id": "act_test",
        "tool_name": "file_writer",
        "risk_level": "RESTRICTED",
        "arguments": {"path": "test.txt", "content": "hello"}
    })

    assert dialog.btn_approve is not None
    assert dialog.btn_reject is not None
