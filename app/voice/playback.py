"""Playback manager handling audio stream queueing and barge-in interruption."""

import queue
import threading
import time
from typing import Any, Dict, Optional, Iterable
from app.core.logger import JarvisLogger

logger = JarvisLogger.get_logger("playback")


class PlaybackManager:
    """Thread-safe playback manager supporting streaming audio and barge-in interruption."""

    def __init__(self, sample_rate: int = 16000, channels: int = 1) -> None:
        self._sample_rate = sample_rate
        self._channels = channels
        self._queue: queue.Queue = queue.Queue()
        self._is_playing: bool = False
        self._stop_event: threading.Event = threading.Event()
        self._lock: threading.Lock = threading.Lock()
        self._worker_thread: Optional[threading.Thread] = None

    def enqueue_chunk(self, audio_data: bytes) -> None:
        """Enqueues PCM audio chunk for playback."""
        if self._stop_event.is_set():
            return
        self._queue.put(audio_data)

    def stream_playback(self, audio_stream: Iterable[bytes]) -> None:
        """Streams audio chunks to speaker until complete or interrupted."""
        with self._lock:
            self._stop_event.clear()
            self._is_playing = True

        try:
            for chunk in audio_stream:
                if self._stop_event.is_set():
                    logger.info("Playback stream interrupted mid-generation.")
                    break
                self.enqueue_chunk(chunk)
                time.sleep(0.01)
        finally:
            with self._lock:
                self._is_playing = False

    def is_playing(self) -> bool:
        """Returns True if audio playback is currently active."""
        with self._lock:
            return self._is_playing or not self._queue.empty()

    def interrupt(self, reason: str = "Barge-in detected") -> None:
        """Instantly interrupts playback, clears audio queue, and stops TTS."""
        with self._lock:
            logger.info(f"Interrupting audio playback (Reason: {reason}).")
            self._stop_event.set()
            self._is_playing = False
            # Clear remaining queue items
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    break

    def stop(self) -> None:
        """Stops playback and resets state."""
        self.interrupt(reason="Stop requested")

    def health_check(self) -> Dict[str, Any]:
        """Returns diagnostic status details."""
        return {
            "is_playing": self.is_playing(),
            "queue_size": self._queue.qsize(),
            "interrupted": self._stop_event.is_set(),
            "sample_rate": self._sample_rate
        }
