"""Deterministic Energy-based Voice Activity Detector (VAD) implementation."""

import time
from typing import List, Optional
import numpy as np

from app.voice.interfaces import VoiceActivityDetector
from app.voice.models import AudioFrame, AudioSegment
from app.core.logger import JarvisLogger

logger = JarvisLogger.get_logger("vad")


class EnergyBasedVAD(VoiceActivityDetector):
    """Detects speech using RMS energy logic and timing constraints."""

    def __init__(
        self,
        threshold: float = 300.0,
        wait_timeout: float = 10.0,
        min_speech_duration: float = 0.25,
        max_utterance_duration: float = 30.0,
        end_silence_duration: float = 0.8,
    ) -> None:
        """Initializes the VAD with parameters.

        Args:
            threshold: RMS energy threshold above which a frame contains speech.
            wait_timeout: Max seconds to wait for speech start before timing out.
            min_speech_duration: Min speech duration in seconds to treat as valid utterance.
            max_utterance_duration: Max speech duration in seconds before forcing completion.
            end_silence_duration: Trailing silence duration in seconds to trigger completion.
        """
        self._threshold = threshold
        self._wait_timeout = wait_timeout
        self._min_speech_duration = min_speech_duration
        self._max_utterance_duration = max_utterance_duration
        self._end_silence_duration = end_silence_duration

        # State tracking
        self._state: str = "WAITING_FOR_SPEECH"  # WAITING_FOR_SPEECH, SPEECH_ACTIVE, COMPLETE, TIMEOUT, ERROR
        self._frames: List[AudioFrame] = []
        self._start_time: float = time.monotonic()
        self._speech_start_time: Optional[float] = None
        self._silence_start_time: Optional[float] = None
        self._sample_rate: int = 16000
        self._channels: int = 1
        self._sample_width: int = 2

    def process_frame(self, frame: AudioFrame) -> None:
        """Evaluates incoming frame and advances the state machine."""
        if self._state in ("COMPLETE", "TIMEOUT", "ERROR"):
            return

        self._sample_rate = frame.sample_rate
        self._channels = frame.channels
        self._sample_width = frame.sample_width

        # Calculate RMS energy of 16-bit PCM data
        try:
            samples = np.frombuffer(frame.pcm_data, dtype=np.int16)
            if len(samples) == 0:
                rms = 0.0
            else:
                rms = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))
        except Exception as e:
            logger.error(f"Error calculating RMS energy of audio frame: {e}")
            self._state = "ERROR"
            return

        now = time.monotonic()

        if self._state == "WAITING_FOR_SPEECH":
            # Append all frames so we have the initial speech start context
            self._frames.append(frame)
            
            # Check timeout
            if (now - self._start_time) > self._wait_timeout:
                logger.info(f"VAD timeout: No speech detected within {self._wait_timeout}s.")
                self._state = "TIMEOUT"
                return

            if rms >= self._threshold:
                logger.info(f"Speech start boundary detected (RMS: {rms:.1f} >= {self._threshold}). Transition to SPEECH_ACTIVE.")
                self._state = "SPEECH_ACTIVE"
                self._speech_start_time = now
                self._silence_start_time = None

        elif self._state == "SPEECH_ACTIVE":
            self._frames.append(frame)
            speech_dur = now - self._speech_start_time

            # Enforce max duration limit
            if speech_dur > self._max_utterance_duration:
                logger.info(f"VAD max duration limit reached ({self._max_utterance_duration}s). Forcing completion.")
                self._state = "COMPLETE"
                return

            if rms < self._threshold:
                if self._silence_start_time is None:
                    self._silence_start_time = now
                elif (now - self._silence_start_time) >= self._end_silence_duration:
                    actual_speech_dur = self._silence_start_time - self._speech_start_time
                    if actual_speech_dur >= self._min_speech_duration:
                        logger.info(f"Speech end boundary detected. Silence for {self._end_silence_duration}s. Speech duration: {actual_speech_dur:.2f}s. Transition to COMPLETE.")
                        self._state = "COMPLETE"
                    else:
                        logger.info(f"Transient noise ignored. Speech duration {actual_speech_dur:.2f}s < {self._min_speech_duration}s. Resetting VAD.")
                        self.reset()
            else:
                # Speech continues, reset silence timer
                self._silence_start_time = None

    def is_speech_active(self) -> bool:
        return self._state == "SPEECH_ACTIVE"

    def has_speech_started(self) -> bool:
        return self._speech_start_time is not None

    def has_speech_ended(self) -> bool:
        return self._state == "COMPLETE"

    def get_captured_segment(self) -> Optional[AudioSegment]:
        if self._state != "COMPLETE" or not self._frames:
            return None

        # Build raw PCM bytes from frames list
        pcm_bytes = b"".join(f.pcm_data for f in self._frames)
        
        # Calculate actual duration
        duration = len(pcm_bytes) / (self._sample_rate * self._channels * self._sample_width)

        return AudioSegment(
            pcm_data=pcm_bytes,
            sample_rate=self._sample_rate,
            channels=self._channels,
            sample_width=self._sample_width,
            duration_seconds=duration
        )

    def reset(self) -> None:
        self._state = "WAITING_FOR_SPEECH"
        self._frames = []
        self._start_time = time.monotonic()
        self._speech_start_time = None
        self._silence_start_time = None

    def get_state(self) -> str:
        return self._state
