"""Unit tests for KnowledgeController."""

import os
import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.gui.knowledge.controller import KnowledgeController


def test_knowledge_controller_ingest():
    app = QApplication.instance() or QApplication([])

    ctrl = KnowledgeController()
    docs = []
    ctrl.documents_updated.connect(lambda d: docs.extend(d))

    ctrl.ingest_files(["test.md"])
    if ctrl.active_worker:
        ctrl.active_worker.wait(2000)
    app.processEvents()

    assert len(docs) == 1
    assert docs[0]["filename"] == "test.md"
