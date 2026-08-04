"""MemoryDetailsWidget inspector panel showing memory record details and metadata."""

from typing import Any, Dict, Optional
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import Qt


class MemoryDetailsWidget(QFrame):
    """Inspector panel rendering selected memory properties and provenance."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.setStyleSheet("background-color: #1a1d29; border: 1px solid #242838; border-radius: 8px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        lbl_hdr = QLabel("🔍 Memory Record Inspector")
        lbl_hdr.setStyleSheet("font-weight: 600; color: #818cf8; font-size: 12px;")
        layout.addWidget(lbl_hdr)

        self.lbl_content = QLabel("Select a memory record from the table to view details.")
        self.lbl_content.setWordWrap(True)
        self.lbl_content.setStyleSheet("color: #e2e8f0; font-size: 13px;")
        layout.addWidget(self.lbl_content)

        layout.addSpacing(8)

        self.lbl_type = QLabel("Type: -")
        self.lbl_type.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(self.lbl_type)

        self.lbl_importance = QLabel("Importance: -")
        self.lbl_importance.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(self.lbl_importance)

        self.lbl_source = QLabel("Source: -")
        self.lbl_source.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(self.lbl_source)

        self.lbl_created = QLabel("Created: -")
        self.lbl_created.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(self.lbl_created)

    def set_memory(self, memory_dict: Dict[str, Any]) -> None:
        """Sets selected memory data."""
        self.lbl_content.setText(memory_dict.get("content", "No Content"))
        self.lbl_type.setText(f"Type: {memory_dict.get('type', 'Fact')}")
        self.lbl_importance.setText(f"Importance: {memory_dict.get('importance', 'High')}")
        self.lbl_source.setText(f"Source: {memory_dict.get('source', 'User Input')}")
        self.lbl_created.setText(f"Created: {memory_dict.get('created_at', 'Just now')}")
