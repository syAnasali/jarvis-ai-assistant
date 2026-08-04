"""Voice View placeholder widget."""

from typing import Optional
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import Qt


class VoiceView(QWidget):
    """Placeholder view for Offline Voice Subsystem."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)

        frame = QFrame()
        frame.setObjectName("cardFrame")
        f_layout = QVBoxLayout(frame)

        lbl = QLabel("Offline Voice Runtime")
        lbl.setObjectName("headerTitle")
        lbl.setAlignment(Qt.AlignCenter)
        f_layout.addWidget(lbl)

        sub = QLabel("Wake word detection, STT transcription, and Piper TTS audio synthesis.")
        sub.setAlignment(Qt.AlignCenter)
        f_layout.addWidget(sub)

        layout.addWidget(frame)
