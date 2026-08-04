"""Unit tests for VoiceActivityDetector (EnergyBasedVAD)."""

import pytest
import numpy as np
from datetime import datetime, timezone
from app.voice.vad import EnergyBasedVAD
from app.voice.models import AudioFrame


def test_vad_initialization_state():
    vad = EnergyBasedVAD(threshold=200.0, wait_timeout=5.0)
    assert vad.get_state() == "WAITING_FOR_SPEECH"
    assert vad.is_speech_active() is False
    assert vad.has_speech_started() is False
    assert vad.has_speech_ended() is False
    assert vad.get_captured_segment() is None


def test_vad_speech_start_and_end():
    vad = EnergyBasedVAD(threshold=100.0, end_silence_duration=0.1, min_speech_duration=0.0)

    # Silent frame
    silent_pcm = np.zeros(1600, dtype=np.int16).tobytes()
    frame1 = AudioFrame(
        pcm_data=silent_pcm,
        sample_rate=16000,
        channels=1,
        sample_width=2,
        timestamp=datetime.now(timezone.utc)
    )
    vad.process_frame(frame1)
    assert vad.get_state() == "WAITING_FOR_SPEECH"

    # Loud speech frame
    loud_pcm = (np.ones(3200, dtype=np.int16) * 5000).tobytes()
    frame2 = AudioFrame(
        pcm_data=loud_pcm,
        sample_rate=16000,
        channels=1,
        sample_width=2,
        timestamp=datetime.now(timezone.utc)
    )
    vad.process_frame(frame2)
    assert vad.is_speech_active() is True
    assert vad.has_speech_started() is True

    # First silence frame sets silence_start_time
    vad.process_frame(frame1)
    # Second silence frame after end_silence_duration completes utterance
    import time
    time.sleep(0.12)
    vad.process_frame(frame1)
    assert vad.has_speech_ended() is True
    seg = vad.get_captured_segment()
    assert seg is not None
    assert seg.duration_seconds > 0.0


def test_vad_reset():
    vad = EnergyBasedVAD()
    vad.reset()
    assert vad.get_state() == "WAITING_FOR_SPEECH"
    assert vad.get_captured_segment() is None
