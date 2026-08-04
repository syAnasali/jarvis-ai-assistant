"""Vision View placeholder widget."""

from typing import Optional
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import Qt


class VisionView(QWidget):
    """Placeholder view for Local Vision Runtime & Desktop Inspection."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)

        frame = QFrame()
        frame.setObjectName("cardFrame")
        f_layout = QVBoxLayout(frame)

        lbl = QLabel("Local Vision Runtime")
        lbl.setObjectName("headerTitle")
        lbl.setAlignment(Qt.AlignCenter)
        f_layout.addWidget(lbl)

        sub = QLabel("Screen capture, region selection, clipboard image OCR, and chart analysis.")
        sub.setAlignment(Qt.AlignCenter)
        f_layout.addWidget(sub)

        layout.addWidget(frame)
