"""ObservabilityController managing QTimer background refresh and QThread workers."""

from typing import Any, Dict, Optional
from PySide6.QtCore import QObject, QTimer, Signal
from app.core.logger import JarvisLogger
from app.gui.observability.worker import ObservabilityWorker

logger = JarvisLogger.get_logger("gui_observability_controller")


class ObservabilityController(QObject):
    """Controller orchestrating Observability Dashboard telemetry refresh and exports."""

    metrics_updated = Signal(dict)
    health_updated = Signal(dict)
    export_finished = Signal(str)
    status_updated = Signal(str)

    def __init__(self, observability_mgr: Optional[Any] = None, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.observability_mgr = observability_mgr
        self.active_worker: Optional[ObservabilityWorker] = None

        # Auto-refresh timer (every 1 second)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_telemetry)
        self.refresh_timer.start(1000)

    def refresh_telemetry(self) -> None:
        """Triggers background telemetry collection worker."""
        if self.active_worker and self.active_worker.isRunning():
            return

        self.active_worker = ObservabilityWorker(action="refresh", observability_mgr=self.observability_mgr, parent=self)
        self.active_worker.metrics_updated.connect(self.metrics_updated.emit)
        self.active_worker.health_updated.connect(self.health_updated.emit)
        self.active_worker.status_changed.connect(self.status_updated.emit)
        self.active_worker.start()

    def export_telemetry(self, fmt: str, path: str) -> None:
        """Triggers background export worker."""
        if self.active_worker and self.active_worker.isRunning():
            self.active_worker.wait()

        self.active_worker = ObservabilityWorker(action="export", export_format=fmt, export_path=path, observability_mgr=self.observability_mgr, parent=self)
        self.active_worker.export_completed.connect(self.export_finished.emit)
        self.active_worker.status_changed.connect(self.status_updated.emit)
        self.active_worker.start()
