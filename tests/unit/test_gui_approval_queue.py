"""Unit tests for ApprovalQueueWidget and RiskBadgeWidget."""

import os
import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.gui.approval import ApprovalQueueWidget, RiskBadgeWidget


def test_approval_queue_and_risk_badge():
    app = QApplication.instance() or QApplication([])

    badge = RiskBadgeWidget("SAFE")
    assert "SAFE" in badge.text()

    queue = ApprovalQueueWidget()
    assert len(queue.pending_actions) >= 2
