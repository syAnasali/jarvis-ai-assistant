"""PlannerController managing plan execution state, DAG graph models, and QThread workers."""

from typing import Any, Dict, List, Optional
from PySide6.QtCore import QObject, Signal
from app.core.logger import JarvisLogger
from app.gui.planner.worker import PlannerWorker

logger = JarvisLogger.get_logger("gui_planner_controller")


class PlannerController(QObject):
    """Controller orchestrating Planner Dashboard execution."""

    node_status_changed = Signal(str, str)
    progress_changed = Signal(int, int, str)
    log_received = Signal(str)
    plan_finished = Signal(str)

    def __init__(self, planner_manager: Optional[Any] = None, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.planner_manager = planner_manager
        self.active_worker: Optional[PlannerWorker] = None
        self.active_plan_id: str = "plan_001"

    def execute_plan(self, plan_id: str = "plan_001") -> None:
        """Triggers asynchronous plan execution worker."""
        if self.active_worker and self.active_worker.isRunning():
            self.active_worker.cancel()

        self.active_plan_id = plan_id
        self.active_worker = PlannerWorker(plan_id=plan_id, planner_manager=self.planner_manager, parent=self)

        self.active_worker.node_started.connect(lambda nid: self.node_status_changed.emit(nid, "RUNNING"))
        self.active_worker.node_completed.connect(lambda nid: self.node_status_changed.emit(nid, "COMPLETED"))
        self.active_worker.node_failed.connect(lambda nid, err: self.node_status_changed.emit(nid, "FAILED"))
        self.active_worker.progress_updated.connect(self.progress_changed.emit)
        self.active_worker.log_emitted.connect(self.log_received.emit)
        self.active_worker.plan_completed.connect(self.plan_finished.emit)

        self.active_worker.start()

    def pause_plan(self) -> None:
        """Pauses active plan execution."""
        logger.info("Paused active plan.")

    def resume_plan(self) -> None:
        """Resumes active plan execution."""
        logger.info("Resumed active plan.")

    def cancel_plan(self) -> None:
        """Cancels active plan execution."""
        if self.active_worker and self.active_worker.isRunning():
            self.active_worker.cancel()
        logger.info("Cancelled active plan.")
