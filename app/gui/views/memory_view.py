"""MemoryView assembling MemorySearchWidget, MemoryFilterWidget, MemoryBrowserWidget, and MemoryDetailsWidget."""

from typing import Any, Dict, Optional
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt
from app.gui.memory.browser import MemoryBrowserWidget
from app.gui.memory.controller import MemoryController
from app.gui.memory.details import MemoryDetailsWidget
from app.gui.memory.editor import MemoryEditorWidget
from app.gui.memory.filters import MemoryFilterWidget
from app.gui.memory.search import MemorySearchWidget


class MemoryView(QWidget):
    """Memory Center interface powering multi-type long-term memory records."""

    def __init__(self, memory_manager: Optional[Any] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.controller = MemoryController(memory_manager=memory_manager, parent=self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. Header Toolbar
        hdr_layout = QHBoxLayout()
        lbl_title = QLabel("Multi-Type Long-Term Memory System")
        lbl_title.setObjectName("headerTitle")
        hdr_layout.addWidget(lbl_title)
        hdr_layout.addStretch()

        self.search_widget = MemorySearchWidget(self)
        self.search_widget.textChanged.connect(self.controller.search_memories)
        hdr_layout.addWidget(self.search_widget)

        self.filter_widget = MemoryFilterWidget(self)
        hdr_layout.addWidget(self.filter_widget)

        self.btn_add = QPushButton("➕ Add Fact")
        self.btn_add.setStyleSheet("background-color: #6366f1; color: #ffffff; font-weight: 600; padding: 4px 12px;")
        self.btn_add.clicked.connect(self._on_add_clicked)
        hdr_layout.addWidget(self.btn_add)

        layout.addLayout(hdr_layout)

        # 2. Main Splitter (Left: Table Browser | Right: Inspector Details)
        splitter = QSplitter(Qt.Horizontal)

        self.browser = MemoryBrowserWidget(self)
        splitter.addWidget(self.browser)

        self.details_inspector = MemoryDetailsWidget(self)
        splitter.addWidget(self.details_inspector)

        splitter.setSizes([600, 400])
        layout.addWidget(splitter)

        # Wire Signals
        self.browser.memory_selected.connect(self.details_inspector.set_memory)
        self.controller.records_loaded.connect(self.browser.populate_table)

    def _on_add_clicked(self) -> None:
        dialog = MemoryEditorWidget(parent=self)
        if dialog.exec():
            content, mtype = dialog.get_data()
            if content:
                new_rec = {
                    "id": f"mem_{len(self.browser.memories) + 1:02d}",
                    "type": mtype,
                    "content": content,
                    "importance": "High",
                    "source": "Manual GUI Entry",
                    "created_at": "Just now"
                }
                self.browser.memories.append(new_rec)
                self.browser.populate_table(self.browser.memories)
