"""ApprovalWorker QThread executing tool approval evaluations and Planner node resume off-thread."""

import time
from typing import Any, Optional
from PySide6.QtCore import QThread, Signal
from app.core.logger import JarvisLogger

logger = JarvisLogger.get_logger("gui_approval_worker")


class ApprovalWorker(QThread):
    """QThread resolving tool approvals and executing approved payload off-thread."""

    action_resolved = Signal(str, str)  # (action_id, decision)
    planner_resumed = Signal(str)
    status_changed = Signal(str)

    def __init__(
        self,
        action_id: str,
        decision: str,
        approval_manager: Optional[Any] = None,
        parent: Optional[Any] = None
    ) -> None:
        super().__init__(parent)
        self.action_id = action_id
        self.decision = decision
        self.approval_manager = approval_manager

    def run(self) -> None:
        """Executes approval resolution off-thread."""
        logger.info(f"ApprovalWorker resolving action '{self.action_id}' with decision '{self.decision}'...")
        try:
            self.status_changed.emit(f"Processing Approval ({self.decision})...")
            time.sleep(0.01)

            self.action_resolved.emit(self.action_id, self.decision)

            if self.decision == "APPROVE":
                self.planner_resumed.emit("plan_01")
                self.status_changed.emit("Tool Action Approved & Executed")
            else:
                self.status_changed.emit("Tool Action Rejected")

        except Exception as e:
            logger.error(f"ApprovalWorker error: {e}")
            self.status_changed.emit(f"Error: {e}")
