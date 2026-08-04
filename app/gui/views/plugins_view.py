"""Plugins View placeholder widget."""

from typing import Optional
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import Qt


class PluginsView(QWidget):
    """Placeholder view for Plugin Manager & Extension Framework."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)

        frame = QFrame()
        frame.setObjectName("cardFrame")
        f_layout = QVBoxLayout(frame)

        lbl = QLabel("Plugin Manager & Extensions")
        lbl.setObjectName("headerTitle")
        lbl.setAlignment(Qt.AlignCenter)
        f_layout.addWidget(lbl)

        sub = QLabel("Installed plugins, permissions, health status, and hot-reload controls.")
        sub.setAlignment(Qt.AlignCenter)
        f_layout.addWidget(sub)

        layout.addWidget(frame)
