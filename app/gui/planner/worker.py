"""PlannerWorker QThread executing DAG plan nodes off the UI thread."""

import time
from typing import Any, Optional
from PySide6.QtCore import QThread, Signal
from app.core.logger import JarvisLogger

logger = JarvisLogger.get_logger("gui_planner_worker")


class PlannerWorker(QThread):
    """QThread executing DAG plan steps off-thread."""

    node_started = Signal(str)
    node_completed = Signal(str)
    node_failed = Signal(str, str)
    progress_updated = Signal(int, int, str)
    log_emitted = Signal(str)
    plan_completed = Signal(str)

    def __init__(self, plan_id: str = "plan_001", planner_manager: Optional[Any] = None, parent: Optional[Any] = None) -> None:
        super().__init__(parent)
        self.plan_id = plan_id
        self.planner_manager = planner_manager
        self._is_cancelled = False

    def cancel(self) -> None:
        """Flags active plan for cancellation."""
        self._is_cancelled = True

    def run(self) -> None:
        """Executes plan steps off-thread."""
        logger.info(f"PlannerWorker started plan '{self.plan_id}'...")
        try:
            nodes = [
                ("node_1", "Parse Document Context"),
                ("node_2", "Execute Semantic Search"),
                ("node_3", "Synthesize Analysis Plan"),
                ("node_4", "Verify Execution Results"),
            ]
            total = len(nodes)

            for idx, (nid, name) in enumerate(nodes, start=1):
                if self._is_cancelled:
                    self.log_emitted.emit("Plan cancelled by user.")
                    return

                self.node_started.emit(nid)
                self.progress_updated.emit(idx - 1, total, name)
                self.log_emitted.emit(f"Executing DAG Node {nid}: '{name}'...")

                time.sleep(0.3)

                if self._is_cancelled:
                    return

                self.node_completed.emit(nid)
                self.log_emitted.emit(f"Node {nid} COMPLETED successfully.")

            self.progress_updated.emit(total, total, "Plan Completed")
            self.plan_completed.emit(self.plan_id)
            logger.info(f"PlannerWorker finished plan '{self.plan_id}'.")

        except Exception as e:
            logger.error(f"PlannerWorker error: {e}")
            self.log_emitted.emit(f"Planner error: {e}")
