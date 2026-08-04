"""Unit tests for VoiceController."""

import os
import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.gui.voice.controller import VoiceController


def test_voice_controller():
    app = QApplication.instance() or QApplication([])

    ctrl = VoiceController()
    transcripts = []
    ctrl.transcript_updated.connect(lambda t: transcripts.append(t))

    ctrl.start_listening()
    if ctrl.active_worker:
        ctrl.active_worker.wait(2000)
    app.processEvents()

    if ctrl.active_worker:
        ctrl.active_worker.wait(2000)
    app.processEvents()

    assert len(transcripts) > 0
