"""Unit tests for VoiceView."""

import os
import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.gui.views.voice_view import VoiceView


def test_voice_view_interaction():
    app = QApplication.instance() or QApplication([])

    view = VoiceView()
    view.btn_talk.click()

    if view.controller.active_worker:
        view.controller.active_worker.wait(2000)
    app.processEvents()

    if view.controller.active_worker:
        view.controller.active_worker.wait(2000)
    app.processEvents()

    assert view.session_widget.lbl_user_transcript.text() != ""
