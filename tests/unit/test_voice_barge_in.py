"""Unit tests for barge-in speech interruption."""

import pytest
from app.voice.pipeline import VoicePipeline
from app.voice.stt import FasterWhisperSTTProvider
from app.voice.tts import PiperProvider
from app.voice.vad import EnergyBasedVAD
from app.voice.playback import PlaybackManager
from app.voice.models import VoiceState


def test_barge_in_interruption_triggers_cleanly():
    stt = FasterWhisperSTTProvider(model_size="tiny")
    tts = PiperProvider()
    vad = EnergyBasedVAD()
    playback = PlaybackManager()

    pipeline = VoicePipeline(
        stt_provider=stt,
        tts_provider=tts,
        vad_detector=vad,
        playback_manager=playback
    )
    pipeline.initialize()

    pipeline.session.transition_to(VoiceState.SPEAKING)
    playback.enqueue_chunk(b"\x00\x00" * 500)

    pipeline.trigger_barge_in()

    assert pipeline.session.state == VoiceState.INTERRUPTED
    assert playback.health_check()["interrupted"] is True
    assert playback.health_check()["queue_size"] == 0

    pipeline.shutdown()
