"""Unit tests for spoken voice action approval response parsing and execution."""

import pytest
from unittest.mock import MagicMock
from app.voice.pipeline import VoicePipeline
from app.voice.stt import FasterWhisperSTTProvider
from app.voice.tts import PiperProvider
from app.voice.vad import EnergyBasedVAD
from app.voice.models import VoiceState


def test_voice_approval_response_accept():
    stt = FasterWhisperSTTProvider(model_size="tiny")
    tts = PiperProvider()
    vad = EnergyBasedVAD()
    approval_mgr = MagicMock()

    pipeline = VoicePipeline(
        stt_provider=stt,
        tts_provider=tts,
        vad_detector=vad,
        approval_manager=approval_mgr
    )
    pipeline.initialize()
    pipeline.session.transition_to(VoiceState.WAITING_APPROVAL)

    res = pipeline._handle_spoken_approval_response("Yes, I approve")
    assert res == "Approved"
    assert pipeline.session.state == VoiceState.LISTENING
    pipeline.shutdown()


def test_voice_approval_response_reject():
    stt = FasterWhisperSTTProvider(model_size="tiny")
    tts = PiperProvider()
    vad = EnergyBasedVAD()
    approval_mgr = MagicMock()

    pipeline = VoicePipeline(
        stt_provider=stt,
        tts_provider=tts,
        vad_detector=vad,
        approval_manager=approval_mgr
    )
    pipeline.initialize()
    pipeline.session.transition_to(VoiceState.WAITING_APPROVAL)

    res = pipeline._handle_spoken_approval_response("No, cancel that")
    assert res == "Rejected"
    assert pipeline.session.state == VoiceState.LISTENING
    pipeline.shutdown()
