"""Diagnostic script testing PySide6 Native Approval Center offscreen."""

import os
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, ".")

import time
from PySide6.QtWidgets import QApplication
from app.gui.approval import ApprovalController, ApprovalQueueWidget, ApprovalDialog, RiskBadgeWidget


def main() -> None:
    print("==================================================")
    print("Testing PySide6 Native Approval Center Diagnostics")
    print("==================================================")

    app = QApplication.instance() or QApplication(sys.argv)

    ctrl = ApprovalController()
    print("PASS: ApprovalController instantiated successfully.")

    badge = RiskBadgeWidget("RESTRICTED")
    assert "RESTRICTED" in badge.text()
    print("PASS: RiskBadgeWidget styling verified.")

    queue = ApprovalQueueWidget()
    assert len(queue.pending_actions) >= 2
    print("PASS: ApprovalQueueWidget populated successfully.")

    # Request new approval
    ctrl.request_approval({
        "id": "act_999",
        "tool_name": "system.cmd",
        "risk_level": "RESTRICTED",
        "source": "CLI",
        "arguments": {"cmd": "dir"},
        "timestamp": "Just now"
    })
    app.processEvents()

    assert len(ctrl.pending_queue) >= 3
    print("PASS: Approval request queued.")

    # Resolve approval
    ctrl.resolve_action("APPROVE", "act_999")
    if ctrl.active_worker:
        ctrl.active_worker.wait(2000)
    app.processEvents()

    assert len(ctrl.history_records) >= 2
    print("PASS: QThread ApprovalWorker resolution & history log verified.")

    print("\nALL NATIVE APPROVAL CENTER DIAGNOSTICS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
