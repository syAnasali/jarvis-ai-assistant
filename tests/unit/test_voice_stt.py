"""Unit tests for the FasterWhisperSTTProvider using mock WhisperModel."""

from unittest.mock import MagicMock, patch
import pytest

from app.voice.models import AudioSegment
from app.voice.stt import FasterWhisperSTTProvider, STTInitializationError


class FakeSegment:
    def __init__(self, text: str) -> None:
        self.text = text
        self.avg_logprob = -0.1


@patch("faster_whisper.WhisperModel")
@patch("ctranslate2.get_cuda_device_count")
def test_stt_provider_lazy_initialization(mock_cuda, mock_whisper_class) -> None:
    mock_cuda.return_value = 0
    mock_model_instance = MagicMock()
    mock_whisper_class.return_value = mock_model_instance

    provider = FasterWhisperSTTProvider(model_size="tiny", device="auto")
    
    # Model not loaded yet
    assert provider._is_initialized is False
    assert provider._model is None

    # Load model
    provider.initialize()
    assert provider._is_initialized is True
    assert provider._model is not None
    assert provider._resolved_device == "cpu"
    
    # Second initialize is no-op
    provider.initialize()
    mock_whisper_class.assert_called_once()

    # Shutdown
    provider.shutdown()
    assert provider._is_initialized is False
    assert provider._model is None


@patch("faster_whisper.WhisperModel")
@patch("ctranslate2.get_cuda_device_count")
def test_stt_transcription_normalization(mock_cuda, mock_whisper_class) -> None:
    mock_cuda.return_value = 0
    mock_model_instance = MagicMock()
    mock_whisper_class.return_value = mock_model_instance

    # Mock transcribe returning segments generator
    mock_model_instance.transcribe.return_value = (
        [FakeSegment("  Hello   world!  "), FakeSegment("\n  Jarvis voice rules. ")],
        MagicMock(language="en", language_probability=0.99)
    )

    provider = FasterWhisperSTTProvider()
    provider.initialize()

    segment = AudioSegment(
        pcm_data=b"\x00\x00" * 32000,
        sample_rate=16000,
        channels=1,
        sample_width=2,
        duration_seconds=2.0
    )

    res = provider.transcribe(segment)

    # Whitespace and segments should be joined and stripped
    assert res.text == "Hello world! Jarvis voice rules."
    assert res.language == "en"
    assert res.metadata["device"] == "cpu"


@patch("faster_whisper.WhisperModel")
def test_stt_empty_transcription(mock_whisper_class) -> None:
    mock_model_instance = MagicMock()
    mock_whisper_class.return_value = mock_model_instance

    # Mock transcribe returning empty segments
    mock_model_instance.transcribe.return_value = (
        [FakeSegment("   \n   ")],
        MagicMock(language="en", language_probability=0.9)
    )

    provider = FasterWhisperSTTProvider()
    provider.initialize()

    segment = AudioSegment(
        pcm_data=b"\x00\x00" * 16000,
        sample_rate=16000,
        channels=1,
        sample_width=2,
        duration_seconds=1.0
    )

    res = provider.transcribe(segment)
    assert res.text == ""
