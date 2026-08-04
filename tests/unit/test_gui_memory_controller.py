"""Unit tests for MemoryController."""

import os
import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.gui.memory.controller import MemoryController


def test_memory_controller_query():
    app = QApplication.instance() or QApplication([])

    ctrl = MemoryController()
    records = []
    ctrl.records_loaded.connect(lambda recs: records.extend(recs))

    ctrl.search_memories("PySide6")
    if ctrl.active_worker:
        ctrl.active_worker.wait(2000)
    app.processEvents()

    assert len(records) > 0
