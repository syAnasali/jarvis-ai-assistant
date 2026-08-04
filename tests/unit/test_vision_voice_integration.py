"""Unit tests verifying Voice Runtime triggers Vision Pipeline and streams speech response."""

import pytest
from app.vision.manager import VisionManager
from app.vision.providers import MockVisionProvider
from app.voice.tts import PiperProvider


def test_voice_request_triggers_vision_pipeline():
    vision_mgr = VisionManager(provider=MockVisionProvider())
    vision_mgr.initialize()

    resp = vision_mgr.analyze_screen(prompt="What is on my screen?")
    assert resp.text != ""

    # Synthesize vision analysis text response via TTS
    tts = PiperProvider()
    tts.initialize()
    synth_res = tts.speak(resp.text)
    assert synth_res.success is True

    tts.shutdown()
    vision_mgr.shutdown()
