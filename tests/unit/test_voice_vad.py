"""Unit tests for the deterministic Energy-based VAD."""

from datetime import datetime, timezone
import time
import pytest

from app.voice.models import AudioFrame
from app.voice.vad import EnergyBasedVAD


def _create_frame(energy: int = 0) -> AudioFrame:
    # 512 samples = 1024 bytes
    pcm = (energy).to_bytes(2, byteorder='little', signed=True) * 512
    return AudioFrame(
        pcm_data=pcm,
        sample_rate=16000,
        channels=1,
        sample_width=2,
        timestamp=datetime.now(timezone.utc)
    )


def test_vad_wait_timeout() -> None:
    # 0.1s wait timeout
    vad = EnergyBasedVAD(threshold=100.0, wait_timeout=0.1)
    
    # Process silence
    frame = _create_frame(0)
    vad.process_frame(frame)
    assert vad.get_state() == "WAITING_FOR_SPEECH"

    # Sleep to trigger timeout
    time.sleep(0.12)
    vad.process_frame(frame)
    assert vad.get_state() == "TIMEOUT"


def test_vad_speech_detection_and_completion() -> None:
    # VAD settings: threshold=100.0, wait=1.0, min_speech=0.05, end_silence=0.1
    vad = EnergyBasedVAD(
        threshold=100.0,
        wait_timeout=1.0,
        min_speech_duration=0.05,
        end_silence_duration=0.1
    )

    # 1. Initially waiting
    assert vad.get_state() == "WAITING_FOR_SPEECH"

    # 2. Feed frames above threshold -> transition to SPEECH_ACTIVE
    vad.process_frame(_create_frame(200))
    assert vad.get_state() == "SPEECH_ACTIVE"
    assert vad.is_speech_active() is True
    assert vad.has_speech_started() is True
    assert vad.has_speech_ended() is False

    # Keep active
    time.sleep(0.06)  # Exceed min speech duration (0.05)
    vad.process_frame(_create_frame(200))
    assert vad.get_state() == "SPEECH_ACTIVE"

    # 3. Feed silence -> starts silence timer
    vad.process_frame(_create_frame(10))
    assert vad.get_state() == "SPEECH_ACTIVE"

    # Sleep to exceed end_silence_duration (0.1)
    time.sleep(0.12)
    vad.process_frame(_create_frame(10))
    assert vad.get_state() == "COMPLETE"
    assert vad.has_speech_ended() is True

    # 4. Get segment
    seg = vad.get_captured_segment()
    assert seg is not None
    assert seg.duration_seconds > 0.0
    assert len(seg.pcm_data) > 0


def test_vad_transient_noise_ignored() -> None:
    # VAD settings: min_speech=0.2s, end_silence=0.05s
    vad = EnergyBasedVAD(
        threshold=100.0,
        wait_timeout=1.0,
        min_speech_duration=0.2,
        end_silence_duration=0.05
    )

    # Starts speech
    vad.process_frame(_create_frame(200))
    assert vad.get_state() == "SPEECH_ACTIVE"

    # Stop speaking immediately (less than min_speech_duration)
    vad.process_frame(_create_frame(0))
    time.sleep(0.07)
    
    # Next frame should trigger reset since speech duration < 0.2s
    vad.process_frame(_create_frame(0))
    assert vad.get_state() == "WAITING_FOR_SPEECH"
    assert vad.get_captured_segment() is None


def test_vad_max_duration() -> None:
    # VAD settings: max_utterance=0.1s
    vad = EnergyBasedVAD(
        threshold=100.0,
        wait_timeout=1.0,
        max_utterance_duration=0.1
    )

    vad.process_frame(_create_frame(200))
    assert vad.get_state() == "SPEECH_ACTIVE"

    # Sleep to exceed max utterance duration
    time.sleep(0.12)
    vad.process_frame(_create_frame(200))
    assert vad.get_state() == "COMPLETE"
