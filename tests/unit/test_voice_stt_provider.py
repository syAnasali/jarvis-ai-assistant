"""Unit tests for SpeechToTextProvider and FasterWhisperSTTProvider."""

import pytest
from app.voice.stt import FasterWhisperSTTProvider, FasterWhisperProvider, STTInitializationError
from app.voice.models import AudioSegment, TranscriptionResult, AudioFrame
from datetime import datetime, timezone


def test_stt_provider_instantiation():
    provider = FasterWhisperProvider(model_size="tiny", device="cpu")
    assert provider._model_size == "tiny"
    assert provider._requested_device == "cpu"
    assert provider.health_check()["available"] is False


def test_stt_provider_initialize_and_health_check():
    provider = FasterWhisperProvider(model_size="tiny", device="cpu")
    provider.initialize()
    health = provider.health_check()
    assert health["available"] is True
    assert health["provider"] == "faster_whisper"
    provider.shutdown()
    assert provider.health_check()["available"] is False


def test_stt_provider_transcribe_silent_audio():
    provider = FasterWhisperProvider(model_size="tiny", device="cpu")
    provider.initialize()

    pcm = b"\x00\x00" * 8000
    segment = AudioSegment(
        pcm_data=pcm,
        sample_rate=16000,
        channels=1,
        sample_width=2,
        duration_seconds=0.5
    )

    result = provider.transcribe(segment)
    assert isinstance(result, TranscriptionResult)
    assert isinstance(result.text, str)
    assert result.duration_seconds >= 0.0
    provider.shutdown()


def test_stt_provider_stream_transcribe():
    provider = FasterWhisperProvider(model_size="tiny", device="cpu")
    provider.initialize()

    frame = AudioFrame(
        pcm_data=b"\x00\x00" * 8000,
        sample_rate=16000,
        channels=1,
        sample_width=2,
        timestamp=datetime.now(timezone.utc)
    )

    results = list(provider.stream_transcribe([frame]))
    assert len(results) >= 1
    assert isinstance(results[0], TranscriptionResult)
    provider.shutdown()
