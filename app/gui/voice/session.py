"""VoiceSessionWidget displaying live transcripts, wake word status, and barge-in controls."""

from typing import Optional
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Signal, Qt


class VoiceSessionWidget(QWidget):
    """Voice session widget presenting live spoken transcripts and interrupt controls."""

    interrupt_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Status Badge Row
        status_row = QHBoxLayout()
        self.lbl_wakeword = QLabel("🟢 Wake-Word: Active ('Jarvis')")
        self.lbl_wakeword.setStyleSheet("font-weight: 600; color: #10b981; font-size: 12px;")
        status_row.addWidget(self.lbl_wakeword)
        status_row.addStretch()

        self.btn_interrupt = QPushButton("🛑 Interrupt (Barge-in)")
        self.btn_interrupt.setStyleSheet("background-color: #ef4444; color: #ffffff; font-weight: 600; padding: 4px 10px; border-radius: 4px;")
        self.btn_interrupt.clicked.connect(self.interrupt_requested.emit)
        status_row.addWidget(self.btn_interrupt)

        layout.addLayout(status_row)

        # Transcript Frame
        frame = QFrame()
        frame.setObjectName("cardFrame")
        f_layout = QVBoxLayout(frame)
        f_layout.setContentsMargins(12, 10, 12, 10)
        f_layout.setSpacing(6)

        lbl_user_hdr = QLabel("🗣️ Spoken User Input:")
        lbl_user_hdr.setStyleSheet("font-weight: 600; color: #818cf8; font-size: 11px;")
        f_layout.addWidget(lbl_user_hdr)

        self.lbl_user_transcript = QLabel("Listening for voice input...")
        self.lbl_user_transcript.setWordWrap(True)
        self.lbl_user_transcript.setStyleSheet("color: #e2e8f0; font-size: 13px;")
        f_layout.addWidget(self.lbl_user_transcript)

        f_layout.addSpacing(8)

        lbl_assistant_hdr = QLabel("🔊 Assistant Speech Output:")
        lbl_assistant_hdr.setStyleSheet("font-weight: 600; color: #6366f1; font-size: 11px;")
        f_layout.addWidget(lbl_assistant_hdr)

        self.lbl_assistant_speech = QLabel("No active speech synthesis.")
        self.lbl_assistant_speech.setWordWrap(True)
        self.lbl_assistant_speech.setStyleSheet("color: #94a3b8; font-size: 13px;")
        f_layout.addWidget(self.lbl_assistant_speech)

        layout.addWidget(frame)

    def set_user_transcript(self, text: str) -> None:
        """Updates user transcript text."""
        self.lbl_user_transcript.setText(text)

    def set_assistant_speech(self, text: str) -> None:
        """Updates assistant speech text."""
        self.lbl_assistant_speech.setText(text)
