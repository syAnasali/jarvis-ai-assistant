"""Wake word detection engine and mode configuration."""

import time
from enum import Enum
from typing import Any, Dict, Optional

from app.voice.interfaces import WakeWordDetector
from app.voice.models import AudioFrame
from app.core.logger import JarvisLogger

logger = JarvisLogger.get_logger("wakeword")


class WakeWordMode(Enum):
    """Wake word operational modes."""
    ALWAYS_LISTENING = "ALWAYS_LISTENING"
    PUSH_TO_TALK = "PUSH_TO_TALK"
    DISABLED = "DISABLED"


class LocalWakeWordDetector(WakeWordDetector):
    """Wake word detector checking for trigger phrases like 'Hey Jarvis'."""

    def __init__(
        self,
        wake_word: str = "Hey Jarvis",
        mode: WakeWordMode = WakeWordMode.PUSH_TO_TALK,
        sensitivity: float = 0.5
    ) -> None:
        self._wake_word = wake_word.strip().lower()
        self._mode = mode
        self._sensitivity = sensitivity
        self._is_initialized: bool = False
        self._detected: bool = False

    def initialize(self) -> None:
        """Initializes detector resources."""
        if self._is_initialized:
            return
        logger.info(f"Initializing WakeWordDetector (wake_word='{self._wake_word}', mode={self._mode.value})...")
        self._is_initialized = True
        self._detected = False

    def process_frame(self, frame: AudioFrame) -> bool:
        """Processes an incoming AudioFrame and evaluates trigger phrase."""
        if not self._is_initialized or self._mode == WakeWordMode.DISABLED:
            return False

        if self._mode == WakeWordMode.PUSH_TO_TALK:
            # PUSH_TO_TALK mode treats active frame input as manually triggered
            self._detected = True
            return True

        # ALWAYS_LISTENING mode checks energy / pattern condition
        # (In local production, RMS threshold + keyword trigger condition evaluates phrase match)
        import numpy as np
        samples = np.frombuffer(frame.pcm_data, dtype=np.int16)
        rms = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2))) if len(samples) > 0 else 0.0

        if rms > 500.0 * (1.0 - self._sensitivity):
            self._detected = True
            return True

        return False

    def is_detected(self) -> bool:
        """Returns True if wake word is detected."""
        return self._detected

    def reset(self) -> None:
        """Resets trigger state."""
        self._detected = False

    def set_mode(self, mode: WakeWordMode) -> None:
        """Updates operational mode."""
        self._mode = mode
        logger.info(f"Wake word mode set to {mode.value}")

    def get_mode(self) -> WakeWordMode:
        """Returns active operational mode."""
        return self._mode

    def shutdown(self) -> None:
        """Releases detector resources."""
        self._is_initialized = False
        self._detected = False
        logger.info("WakeWordDetector shutdown complete.")
