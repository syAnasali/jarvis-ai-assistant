"""Memory View placeholder widget."""

from typing import Optional
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import Qt


class MemoryView(QWidget):
    """Placeholder view for Multi-Type Long-Term Memory System."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)

        frame = QFrame()
        frame.setObjectName("cardFrame")
        f_layout = QVBoxLayout(frame)

        lbl = QLabel("Multi-Type Memory System")
        lbl.setObjectName("headerTitle")
        lbl.setAlignment(Qt.AlignCenter)
        f_layout.addWidget(lbl)

        sub = QLabel("Facts, Preferences, Project Context, and evidence validation records.")
        sub.setAlignment(Qt.AlignCenter)
        f_layout.addWidget(sub)

        layout.addWidget(frame)
