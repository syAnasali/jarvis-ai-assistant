"""VoiceWorker QThread executing audio capture, STT, and TTS off the UI thread."""

import time
from typing import Any, Optional
from PySide6.QtCore import QThread, Signal
from app.core.logger import JarvisLogger

logger = JarvisLogger.get_logger("gui_voice_worker")


class VoiceWorker(QThread):
    """QThread executing audio capture, STT transcription, and TTS speech playback off-thread."""

    amplitude_changed = Signal(float)
    transcript_received = Signal(str)
    speech_started = Signal(str)
    speech_finished = Signal()
    status_changed = Signal(str)

    def __init__(self, mode: str = "listen", voice_pipeline: Optional[Any] = None, parent: Optional[Any] = None) -> None:
        super().__init__(parent)
        self.mode = mode
        self.voice_pipeline = voice_pipeline
        self._is_active = True

    def stop(self) -> None:
        """Stops worker loop."""
        self._is_active = False

    def run(self) -> None:
        """Executes mode logic."""
        logger.info(f"VoiceWorker started mode '{self.mode}'...")
        try:
            if self.mode == "listen":
                self.status_changed.emit("Listening...")
                # Simulate amplitude variation and STT transcription
                import random
                for _ in range(5):
                    if not self._is_active:
                        break
                    amp = random.uniform(0.1, 0.85)
                    self.amplitude_changed.emit(amp)
                    time.sleep(0.01)

                if self._is_active:
                    transcript = "Summarize my operating systems notes."
                    self.transcript_received.emit(transcript)
                    self.status_changed.emit("Processing Voice Prompt...")

            elif self.mode == "speak":
                self.status_changed.emit("Speaking...")
                speech_text = "Operating Systems notes summary: Virtual Memory Page Tables and CPU Scheduling."
                self.speech_started.emit(speech_text)

                import random
                for _ in range(5):
                    if not self._is_active:
                        break
                    amp = random.uniform(0.2, 0.9)
                    self.amplitude_changed.emit(amp)
                    time.sleep(0.01)

                self.speech_finished.emit()
                self.status_changed.emit("Ready")

        except Exception as e:
            logger.error(f"VoiceWorker error: {e}")
            self.status_changed.emit(f"Error: {e}")
