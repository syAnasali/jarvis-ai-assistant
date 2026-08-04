"""MemorySearchWidget search bar for Memory Center."""

from typing import Optional
from PySide6.QtWidgets import QLineEdit, QWidget


class MemorySearchWidget(QLineEdit):
    """Search input box for filtering memory records."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setPlaceholderText("Search facts, preferences, project context...")
        self.setFixedWidth(280)
        self.setStyleSheet("background-color: #1a1d29; border: 1px solid #242838; border-radius: 6px; padding: 4px 8px; color: #e2e8f0;")
