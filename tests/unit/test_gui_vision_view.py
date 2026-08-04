"""Unit tests for VisionView."""

import os
import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.gui.views.vision_view import VisionView


def test_vision_view_capture():
    app = QApplication.instance() or QApplication([])

    view = VisionView()
    view.btn_full.click()

    if view.controller.active_worker:
        view.controller.active_worker.wait(3000)
    app.processEvents()

    assert view.txt_ocr.toPlainText() != ""
