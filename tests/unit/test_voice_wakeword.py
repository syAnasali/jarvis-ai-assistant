"""Unit tests for WakeWordDetector and WakeWordMode."""

import pytest
from datetime import datetime, timezone
import numpy as np
from app.voice.wakeword import LocalWakeWordDetector, WakeWordMode
from app.voice.models import AudioFrame


def test_wakeword_detector_modes():
    detector = LocalWakeWordDetector(wake_word="Hey Jarvis", mode=WakeWordMode.PUSH_TO_TALK)
    detector.initialize()
    assert detector.get_mode() == WakeWordMode.PUSH_TO_TALK

    frame = AudioFrame(
        pcm_data=b"\x00\x00" * 160,
        sample_rate=16000,
        channels=1,
        sample_width=2,
        timestamp=datetime.now(timezone.utc)
    )

    # Push to talk always triggers on input frame
    assert detector.process_frame(frame) is True
    assert detector.is_detected() is True

    detector.reset()
    assert detector.is_detected() is False

    # Disabled mode never triggers
    detector.set_mode(WakeWordMode.DISABLED)
    assert detector.process_frame(frame) is False

    detector.shutdown()


def test_wakeword_detector_always_listening():
    detector = LocalWakeWordDetector(wake_word="Hey Jarvis", mode=WakeWordMode.ALWAYS_LISTENING, sensitivity=0.8)
    detector.initialize()

    loud_pcm = (np.ones(160, dtype=np.int16) * 5000).tobytes()
    frame = AudioFrame(
        pcm_data=loud_pcm,
        sample_rate=16000,
        channels=1,
        sample_width=2,
        timestamp=datetime.now(timezone.utc)
    )

    assert detector.process_frame(frame) is True
    detector.shutdown()
