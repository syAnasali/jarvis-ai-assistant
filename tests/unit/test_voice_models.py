"""Unit tests for the voice subsystem models."""

from datetime import datetime, timezone
import pytest

from app.voice.models import AudioFrame, AudioSegment, TranscriptionResult, SpeechSynthesisResult, VoiceState


def test_audio_frame_validation() -> None:
    # Valid AudioFrame
    frame = AudioFrame(
        pcm_data=b"\x00\x00" * 512,
        sample_rate=16000,
        channels=1,
        sample_width=2,
        timestamp=datetime.now(timezone.utc)
    )
    assert frame.sample_rate == 16000
    assert frame.channels == 1
    assert len(frame.pcm_data) == 1024

    # Invalid empty PCM
    with pytest.raises(ValueError, match="pcm_data cannot be empty"):
        AudioFrame(
            pcm_data=b"",
            sample_rate=16000,
            channels=1,
            sample_width=2,
            timestamp=datetime.now(timezone.utc)
        )

    # Invalid sample rate
    with pytest.raises(ValueError, match="sample_rate must be positive"):
        AudioFrame(
            pcm_data=b"\x00\x00",
            sample_rate=0,
            channels=1,
            sample_width=2,
            timestamp=datetime.now(timezone.utc)
        )

    # Invalid channels
    with pytest.raises(ValueError, match="channels must be 1"):
        AudioFrame(
            pcm_data=b"\x00\x00",
            sample_rate=16000,
            channels=3,
            sample_width=2,
            timestamp=datetime.now(timezone.utc)
        )

    # Invalid sample width
    with pytest.raises(ValueError, match="sample_width must be 1"):
        AudioFrame(
            pcm_data=b"\x00\x00",
            sample_rate=16000,
            channels=1,
            sample_width=3,
            timestamp=datetime.now(timezone.utc)
        )

    # Invalid naive timestamp
    with pytest.raises(ValueError, match="timestamp must be timezone-aware"):
        AudioFrame(
            pcm_data=b"\x00\x00",
            sample_rate=16000,
            channels=1,
            sample_width=2,
            timestamp=datetime.now()  # Naive
        )


def test_audio_frame_repr() -> None:
    frame = AudioFrame(
        pcm_data=b"\x00\x00" * 10,
        sample_rate=16000,
        channels=1,
        sample_width=2,
        timestamp=datetime(2026, 7, 16, 20, 0, 0, tzinfo=timezone.utc)
    )
    rep = repr(frame)
    # Ensure it doesn't print raw bytes but shows size
    assert "pcm_bytes=20" in rep
    assert "b'\\x00'" not in rep


def test_audio_segment_validation() -> None:
    # Valid AudioSegment
    segment = AudioSegment(
        pcm_data=b"\x00\x00" * 16000,
        sample_rate=16000,
        channels=1,
        sample_width=2,
        duration_seconds=1.0
    )
    assert segment.duration_seconds == 1.0

    # Invalid duration
    with pytest.raises(ValueError, match="duration_seconds must be positive"):
        AudioSegment(
            pcm_data=b"\x00\x00",
            sample_rate=16000,
            channels=1,
            sample_width=2,
            duration_seconds=0.0
        )


def test_transcription_result_defensive_metadata() -> None:
    meta = {"raw_tokens": [1, 2, 3]}
    res = TranscriptionResult(text="hello", duration_seconds=1.0, metadata=meta)
    
    # Mutating original dictionary should not affect result metadata
    meta["raw_tokens"].append(4)
    assert res.metadata["raw_tokens"] == [1, 2, 3]

    # Modifying metadata directly should raise error (frozen or read-only MappingProxyType)
    with pytest.raises(TypeError):
        res.metadata["raw_tokens"] = [1]


def test_speech_synthesis_result_validation() -> None:
    with pytest.raises(ValueError, match="duration_seconds must be non-negative"):
        SpeechSynthesisResult(success=True, duration_seconds=-1.0)
