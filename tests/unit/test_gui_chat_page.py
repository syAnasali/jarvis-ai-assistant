"""Unit tests for ChatView interface."""

import os
import time
import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.gui.views.chat_view import ChatView


def test_chat_view_user_input():
    app = QApplication.instance() or QApplication([])

    view = ChatView()
    view.message_input.txt_input.setPlainText("Test input string")
    view.message_input.btn_send.click()

    if view.controller.active_worker:
        view.controller.active_worker.wait(3000)
    app.processEvents()

    assert len(view.controller.active_session.messages) >= 1
