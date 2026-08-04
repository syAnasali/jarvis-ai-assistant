"""VoiceView assembling Push-to-Talk, Always-Listening, WaveformWidget, and VoiceSessionWidget."""

from typing import Any, Optional
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt
from app.gui.voice.controller import VoiceController
from app.gui.voice.microphone import MicrophoneDeviceSelector
from app.gui.voice.session import VoiceSessionWidget
from app.gui.voice.waveform import WaveformWidget


class VoiceView(QWidget):
    """Voice Workspace interface powering offline speech intake and TTS playback."""

    def __init__(self, voice_pipeline: Optional[Any] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.controller = VoiceController(voice_pipeline=voice_pipeline, parent=self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. Header Toolbar
        hdr_layout = QHBoxLayout()
        lbl_title = QLabel("Offline Voice Runtime Workspace")
        lbl_title.setObjectName("headerTitle")
        hdr_layout.addWidget(lbl_title)
        hdr_layout.addStretch()

        lbl_mic = QLabel("Input Device:")
        hdr_layout.addWidget(lbl_mic)
        self.mic_selector = MicrophoneDeviceSelector(self)
        hdr_layout.addWidget(self.mic_selector)

        layout.addLayout(hdr_layout)

        # 2. Control Cards Row
        ctrl_frame = QFrame()
        ctrl_frame.setObjectName("cardFrame")
        c_layout = QHBoxLayout(ctrl_frame)
        c_layout.setContentsMargins(12, 12, 12, 12)
        c_layout.setSpacing(12)

        self.btn_talk = QPushButton("🎤 Push to Talk")
        self.btn_talk.setFixedHeight(40)
        self.btn_talk.setStyleSheet("background-color: #6366f1; color: #ffffff; font-weight: 600; border-radius: 6px;")
        self.btn_talk.clicked.connect(self.controller.start_listening)
        c_layout.addWidget(self.btn_talk)

        self.btn_always = QPushButton("🔄 Always Listening: OFF")
        self.btn_always.setFixedHeight(40)
        self.btn_always.setCheckable(True)
        self.btn_always.setStyleSheet("background-color: #242838; color: #94a3b8; font-weight: 600; border-radius: 6px;")
        self.btn_always.clicked.connect(self._toggle_always)
        c_layout.addWidget(self.btn_always)

        layout.addWidget(ctrl_frame)

        # 3. Waveform Audio Level Meter
        wf_frame = QFrame()
        wf_frame.setObjectName("cardFrame")
        wf_layout = QVBoxLayout(wf_frame)
        wf_layout.setContentsMargins(8, 8, 8, 8)

        lbl_wf = QLabel("Live Microphone Level Meter:")
        lbl_wf.setStyleSheet("color: #94a3b8; font-size: 11px;")
        wf_layout.addWidget(lbl_wf)

        self.waveform = WaveformWidget(num_bars=24, parent=self)
        wf_layout.addWidget(self.waveform)

        layout.addWidget(wf_frame)

        # 4. Session & Transcript Panel
        self.session_widget = VoiceSessionWidget(self)
        layout.addWidget(self.session_widget)

        # Wire Signals
        self.controller.amplitude_updated.connect(self.waveform.set_amplitude)
        self.controller.transcript_updated.connect(self.session_widget.set_user_transcript)
        self.controller.speech_started.connect(self.session_widget.set_assistant_speech)
        self.controller.status_updated.connect(self._on_status_updated)
        self.session_widget.interrupt_requested.connect(self.controller.interrupt)

    def _toggle_always(self) -> None:
        chk = self.btn_always.isChecked()
        if chk:
            self.btn_always.setText("🟢 Always Listening: ON")
            self.btn_always.setStyleSheet("background-color: #065f46; color: #34d399; font-weight: 600; border-radius: 6px;")
        else:
            self.btn_always.setText("🔄 Always Listening: OFF")
            self.btn_always.setStyleSheet("background-color: #242838; color: #94a3b8; font-weight: 600; border-radius: 6px;")

    def _on_status_updated(self, status: str) -> None:
        if "Listening" in status:
            self.session_widget.lbl_wakeword.setText(f"🟢 Wake-Word: Active ({status})")
        else:
            self.session_widget.lbl_wakeword.setText(f"⚪ Voice Status: {status}")
