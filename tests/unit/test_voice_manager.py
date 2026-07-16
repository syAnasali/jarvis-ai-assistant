"""Unit tests for the VoiceManager subsystem coordinator."""

from datetime import datetime, timezone
from unittest.mock import MagicMock
import pytest

from app.voice.models import AudioSegment, TranscriptionResult
from app.voice.manager import VoiceManager


def test_voice_manager_successful_flow() -> None:
    capture_mock = MagicMock()
    vad_mock = MagicMock()
    stt_mock = MagicMock()
    tts_mock = MagicMock()

    # Set up VAD state transition to COMPLETE
    vad_mock.get_state.side_effect = ["WAITING_FOR_SPEECH", "SPEECH_ACTIVE", "COMPLETE", "COMPLETE"]
    
    # Set up capture frame
    frame_mock = MagicMock()
    capture_mock.read_frame.return_value = frame_mock
    
    # Set up VAD captured segment
    segment_mock = AudioSegment(
        pcm_data=b"\x00" * 32000,
        sample_rate=16000,
        channels=1,
        sample_width=2,
        duration_seconds=1.0
    )
    vad_mock.get_captured_segment.return_value = segment_mock

    # Set up STT transcription
    trans_result = TranscriptionResult(text="testing manager", duration_seconds=0.5)
    stt_mock.transcribe.return_value = trans_result

    manager = VoiceManager(capture=capture_mock, vad=vad_mock, stt=stt_mock, tts=tts_mock)
    manager.initialize()

    # Call listen_once
    status, result = manager.listen_once()

    # Assertions
    assert status == "TRANSCRIBED"
    assert result == trans_result
    capture_mock.open_capture.assert_called_once()
    capture_mock.close_capture.assert_called_once()
    vad_mock.reset.assert_called_once()
    stt_mock.transcribe.assert_called_once_with(segment_mock)

    # Check metrics
    assert manager.metrics["listen_requests"] == 1
    assert manager.metrics["speech_detected"] == 1
    assert manager.metrics["successful_transcriptions"] == 1
    assert manager.metrics["total_audio_seconds"] == 1.0


def test_voice_manager_timeout_flow() -> None:
    capture_mock = MagicMock()
    vad_mock = MagicMock()
    stt_mock = MagicMock()
    tts_mock = MagicMock()

    # VAD returns TIMEOUT
    vad_mock.get_state.side_effect = ["WAITING_FOR_SPEECH", "TIMEOUT", "TIMEOUT"]
    
    manager = VoiceManager(capture=capture_mock, vad=vad_mock, stt=stt_mock, tts=tts_mock)
    status, result = manager.listen_once()

    assert status == "TIMEOUT"
    assert result is None
    assert manager.metrics["listen_timeouts"] == 1
    stt_mock.transcribe.assert_not_called()
    capture_mock.close_capture.assert_called_once()


def test_voice_manager_stt_failure_flow() -> None:
    capture_mock = MagicMock()
    vad_mock = MagicMock()
    stt_mock = MagicMock()
    tts_mock = MagicMock()

    vad_mock.get_state.side_effect = ["SPEECH_ACTIVE", "COMPLETE", "COMPLETE"]
    segment_mock = AudioSegment(
        pcm_data=b"\x00" * 32000,
        sample_rate=16000,
        channels=1,
        sample_width=2,
        duration_seconds=1.0
    )
    vad_mock.get_captured_segment.return_value = segment_mock

    # STT raises exception
    stt_mock.transcribe.side_effect = Exception("Model failed")

    manager = VoiceManager(capture=capture_mock, vad=vad_mock, stt=stt_mock, tts=tts_mock)
    status, result = manager.listen_once()

    assert status == "ERROR"
    assert result is None
    assert manager.metrics["stt_failures"] == 1
