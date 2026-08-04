"""ApprovalController managing human-in-the-loop pending queue and QThread workers."""

from typing import Any, Dict, List, Optional
from PySide6.QtCore import QObject, Signal
from app.core.logger import JarvisLogger
from app.gui.approval.worker import ApprovalWorker

logger = JarvisLogger.get_logger("gui_approval_controller")


class ApprovalController(QObject):
    """Controller orchestrating Native Approval Center actions."""

    approval_requested = Signal(dict)
    action_resolved = Signal(str, str)
    queue_updated = Signal(list)
    history_updated = Signal(list)
    status_updated = Signal(str)

    def __init__(self, approval_manager: Optional[Any] = None, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.approval_manager = approval_manager
        self.active_worker: Optional[ApprovalWorker] = None

        self.pending_queue: List[Dict[str, Any]] = [
            {"id": "act_101", "tool_name": "file_writer", "risk_level": "RESTRICTED", "source": "Planner Node #2", "arguments": {"path": "config/settings.json", "content": "{}"}, "timestamp": "10:15:30"},
            {"id": "act_102", "tool_name": "python_eval", "risk_level": "CONFIRMATION", "source": "User Chat", "arguments": {"script": "print('Hello Jarvis')"}, "timestamp": "10:15:42"},
        ]
        self.history_records: List[Dict[str, Any]] = [
            {"id": "app_01", "tool_name": "python_eval", "decision": "APPROVED", "duration": "45 ms", "timestamp": "10:14:02"},
        ]

    def request_approval(self, action_dict: Dict[str, Any]) -> None:
        """Triggers approval request popup."""
        self.pending_queue.append(action_dict)
        self.queue_updated.emit(self.pending_queue)
        self.approval_requested.emit(action_dict)

    def resolve_action(self, decision: str, action_id: str) -> None:
        """Triggers asynchronous approval resolution worker."""
        if self.active_worker and self.active_worker.isRunning():
            self.active_worker.wait()

        self.active_worker = ApprovalWorker(action_id=action_id, decision=decision, approval_manager=self.approval_manager, parent=self)
        self.active_worker.action_resolved.connect(self._on_action_resolved)
        self.active_worker.status_changed.connect(self.status_updated.emit)
        self.active_worker.start()

    def _on_action_resolved(self, action_id: str, decision: str) -> None:
        target = None
        for a in self.pending_queue:
            if a["id"] == action_id:
                target = a
                break

        if target:
            self.pending_queue.remove(target)
            self.queue_updated.emit(self.pending_queue)
            self.history_records.append({
                "id": target["id"],
                "tool_name": target.get("tool_name", "tool"),
                "decision": decision,
                "duration": "12 ms",
                "timestamp": "Just now"
            })
            self.history_updated.emit(self.history_records)

        self.action_resolved.emit(action_id, decision)
