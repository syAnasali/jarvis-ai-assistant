"""Unit tests for voice pipeline error recovery and graceful degradation."""

import pytest
from app.voice.pipeline import VoicePipeline
from app.voice.stt import FasterWhisperSTTProvider
from app.voice.tts import PiperProvider
from app.voice.vad import EnergyBasedVAD
from app.voice.models import AudioSegment, VoiceState


def test_voice_pipeline_handles_transcription_exception(monkeypatch):
    stt = FasterWhisperSTTProvider(model_size="tiny")
    tts = PiperProvider()
    vad = EnergyBasedVAD()

    pipeline = VoicePipeline(
        stt_provider=stt,
        tts_provider=tts,
        vad_detector=vad
    )
    pipeline.initialize()

    def mock_transcribe_fail(segment):
        raise Exception("STT engine simulated crash")

    monkeypatch.setattr(stt, "transcribe", mock_transcribe_fail)

    segment = AudioSegment(
        pcm_data=b"\x00\x00" * 1600,
        sample_rate=16000,
        channels=1,
        sample_width=2,
        duration_seconds=0.1
    )

    with pytest.raises(Exception):
        pipeline.process_utterance(segment)

    pipeline.shutdown()
