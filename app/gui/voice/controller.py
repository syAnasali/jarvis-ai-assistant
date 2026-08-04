"""VoiceController managing voice interaction state, Push-to-Talk, and QThread workers."""

from typing import Any, Optional
from PySide6.QtCore import QObject, Signal
from app.core.logger import JarvisLogger
from app.gui.voice.worker import VoiceWorker

logger = JarvisLogger.get_logger("gui_voice_controller")


class VoiceController(QObject):
    """Controller orchestrating Voice Workspace interactions."""

    amplitude_updated = Signal(float)
    transcript_updated = Signal(str)
    speech_started = Signal(str)
    speech_finished = Signal()
    status_updated = Signal(str)

    def __init__(self, voice_pipeline: Optional[Any] = None, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.voice_pipeline = voice_pipeline
        self.active_worker: Optional[VoiceWorker] = None
        self.always_listening: bool = False


    def start_listening(self) -> None:
        """Triggers Push-to-Talk audio intake worker."""
        if self.active_worker and self.active_worker.isRunning():
            self.active_worker.stop()

        self.active_worker = VoiceWorker(mode="listen", voice_pipeline=self.voice_pipeline, parent=self)
        self.active_worker.amplitude_changed.connect(self.amplitude_updated.emit)
        self.active_worker.transcript_received.connect(self._on_transcript_received)
        self.active_worker.status_changed.connect(self.status_updated.emit)
        self.active_worker.start()

    def _on_transcript_received(self, text: str) -> None:
        """Handles STT transcription and triggers assistant TTS speech output."""
        self.transcript_updated.emit(text)
        self.speak_text("Operating Systems notes summary: Virtual Memory Page Tables and CPU Scheduling.")

    def speak_text(self, text: str) -> None:
        """Triggers assistant TTS speech synthesis worker."""
        if self.active_worker and self.active_worker.isRunning():
            self.active_worker.stop()

        self.active_worker = VoiceWorker(mode="speak", voice_pipeline=self.voice_pipeline, parent=self)
        self.active_worker.amplitude_changed.connect(self.amplitude_updated.emit)
        self.active_worker.speech_started.connect(self.speech_started.emit)
        self.active_worker.speech_finished.connect(self.speech_finished.emit)
        self.active_worker.status_changed.connect(self.status_updated.emit)
        self.active_worker.start()

    def interrupt(self) -> None:
        """Barge-in interrupt request stopping active speech playback."""
        if self.active_worker and self.active_worker.isRunning():
            self.active_worker.stop()
            self.status_updated.emit("Interrupted")
            self.speech_finished.emit()
        logger.info("Voice playback interrupted by user.")
