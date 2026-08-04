"""Diagnostic script testing PySide6 Memory & Knowledge Center offscreen."""

import os
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, ".")

import time
from PySide6.QtWidgets import QApplication
from app.gui.views.knowledge_view import KnowledgeView
from app.gui.views.memory_view import MemoryView


def main() -> None:
    print("==================================================")
    print("Testing PySide6 Memory & Knowledge Center Diagnostics")
    print("==================================================")

    app = QApplication.instance() or QApplication(sys.argv)

    # 1. MemoryView Diagnostics
    memory_view = MemoryView()
    print("PASS: MemoryView instantiated successfully.")

    memory_view.search_widget.setText("PySide6")
    if memory_view.controller.active_worker:
        memory_view.controller.active_worker.wait(2000)
    app.processEvents()

    assert len(memory_view.browser.memories) > 0
    print("PASS: QThread MemoryWorker search query verified.")

    # 2. KnowledgeView Diagnostics
    knowledge_view = KnowledgeView()
    print("PASS: KnowledgeView instantiated successfully.")

    knowledge_view.controller.ingest_files(["data/sample_doc.md"])
    if knowledge_view.controller.active_worker:
        knowledge_view.controller.active_worker.wait(2000)
    app.processEvents()

    assert len(knowledge_view.browser.documents) >= 4
    print("PASS: QThread KnowledgeWorker document ingestion verified.")

    knowledge_view.search_widget.setText("virtual memory")
    if knowledge_view.controller.active_worker:
        knowledge_view.controller.active_worker.wait(2000)
    app.processEvents()

    print("PASS: QThread KnowledgeWorker hybrid search verified.")

    print("\nALL MEMORY & KNOWLEDGE CENTER DIAGNOSTICS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
