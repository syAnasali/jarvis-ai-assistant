"""VisionController managing screen capture workflows, clipboard intake, and QThread workers."""

from typing import Any, List, Optional, Tuple
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QPixmap
from app.core.logger import JarvisLogger
from app.gui.vision.worker import VisionWorker

logger = JarvisLogger.get_logger("gui_vision_controller")


class VisionController(QObject):
    """Controller orchestrating Vision Workspace capture and OCR workflows."""

    image_captured = Signal(object, str)
    ocr_extracted = Signal(str, list)
    reasoning_finished = Signal(str)
    status_updated = Signal(str)

    def __init__(self, vision_pipeline: Optional[Any] = None, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.vision_pipeline = vision_pipeline
        self.active_worker: Optional[VisionWorker] = None
        self.capture_history: List[str] = []

    def capture_screen(self, mode: str = "full_screen", bbox: Optional[Tuple[int, int, int, int]] = None) -> None:
        """Triggers asynchronous screen capture worker."""
        if self.active_worker and self.active_worker.isRunning():
            self.active_worker.wait()

        self.active_worker = VisionWorker(mode=mode, bbox=bbox, vision_pipeline=self.vision_pipeline, parent=self)
        self.active_worker.capture_completed.connect(self._on_capture_completed)
        self.active_worker.ocr_completed.connect(self.ocr_extracted.emit)
        self.active_worker.analysis_completed.connect(self.reasoning_finished.emit)
        self.active_worker.status_changed.connect(self.status_updated.emit)
        self.active_worker.start()

    def _on_capture_completed(self, pixmap: QPixmap, path: str) -> None:
        """Handles capture completion."""
        self.capture_history.append(path)
        self.image_captured.emit(pixmap, path)
        logger.info(f"Captured screen image to '{path}'. Total history: {len(self.capture_history)}")
