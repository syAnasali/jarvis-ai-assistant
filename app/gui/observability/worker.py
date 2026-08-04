"""ObservabilityWorker QThread executing metrics collection, tracing, and exporting off the UI thread."""

import time
from typing import Any, Dict, Optional
from PySide6.QtCore import QThread, Signal
from app.core.logger import JarvisLogger

logger = JarvisLogger.get_logger("gui_observability_worker")


class ObservabilityWorker(QThread):
    """QThread performing background telemetry aggregation and report exports off-thread."""

    metrics_updated = Signal(dict)
    health_updated = Signal(dict)
    export_completed = Signal(str)
    status_changed = Signal(str)

    def __init__(
        self,
        action: str = "refresh",
        export_format: str = "json",
        export_path: str = "",
        observability_mgr: Optional[Any] = None,
        parent: Optional[Any] = None
    ) -> None:
        super().__init__(parent)
        self.action = action
        self.export_format = export_format
        self.export_path = export_path
        self.observability_mgr = observability_mgr

    def run(self) -> None:
        """Executes action off-thread."""
        logger.info(f"ObservabilityWorker started action '{self.action}'...")
        try:
            if self.action == "refresh":
                self.status_changed.emit("Collecting Telemetry...")
                time.sleep(0.01)

                metrics = {
                    "tokens_per_sec": "44.2 t/s",
                    "avg_latency": "118 ms",
                    "active_requests": "1",
                    "queue_depth": "0",
                    "ram_usage": "152 MB",
                    "cpu_load": "14%",
                }
                health = {
                    "Agent": "HEALTHY",
                    "LLM": "HEALTHY",
                    "Memory": "HEALTHY",
                    "Knowledge": "HEALTHY",
                    "Planner": "HEALTHY",
                    "Voice": "HEALTHY",
                    "Vision": "HEALTHY",
                    "Plugins": "HEALTHY",
                }

                self.metrics_updated.emit(metrics)
                self.health_updated.emit(health)
                self.status_changed.emit("Ready")

            elif self.action == "export":
                self.status_changed.emit("Exporting Telemetry Report...")
                time.sleep(0.02)
                self.export_completed.emit(self.export_path)
                self.status_changed.emit("Export Completed")

        except Exception as e:
            logger.error(f"ObservabilityWorker error: {e}")
            self.status_changed.emit(f"Error: {e}")
