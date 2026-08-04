"""Unit tests for VisionController."""

import os
import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.gui.vision.controller import VisionController


def test_vision_controller():
    app = QApplication.instance() or QApplication([])

    ctrl = VisionController()
    ocr_results = []
    ctrl.ocr_extracted.connect(lambda text, ann: ocr_results.append(text))

    ctrl.capture_screen("full_screen")
    if ctrl.active_worker:
        ctrl.active_worker.wait(3000)
    app.processEvents()

    assert len(ocr_results) > 0
    assert len(ctrl.capture_history) > 0
