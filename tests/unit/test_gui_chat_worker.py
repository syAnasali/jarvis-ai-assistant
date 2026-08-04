"""Unit tests for ChatWorker QThread."""

import os
import time
import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.gui.chat.worker import ChatWorker


def test_chat_worker_execution():
    app = QApplication.instance() or QApplication([])

    received_tokens = []

    worker = ChatWorker(prompt="Hello worker test")
    worker.token_received.connect(lambda token: received_tokens.append(token))

    worker.start()
    worker.wait(3000)
    app.processEvents()

    assert len(received_tokens) > 0
