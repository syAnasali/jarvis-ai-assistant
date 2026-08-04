"""Unit tests for TextToSpeechProvider, PiperProvider, and PyTTSx3TTSProvider."""

import pytest
from app.voice.tts import PiperProvider, PyTTSx3TTSProvider, normalize_text_for_speech, TTSInitializationError
from app.voice.models import SpeechSynthesisResult


def test_normalize_text_for_speech():
    raw = "## Heading\nHello `code` world! Check https://example.com and **bold** text."
    normalized = normalize_text_for_speech(raw)
    assert "Heading" in normalized
    assert "code" in normalized
    assert "link" in normalized
    assert "bold" in normalized
    assert "`" not in normalized
    assert "##" not in normalized


def test_piper_provider_initialization():
    piper = PiperProvider(voice="en_US-lessac-medium", speed=1.1, volume=0.9, sample_rate=22050)
    piper.initialize()
    health = piper.health_check()
    assert health["available"] is True
    assert health["provider"] == "piper"
    assert health["speed"] == 1.1
    piper.shutdown()


def test_piper_provider_speak():
    piper = PiperProvider()
    piper.initialize()
    res = piper.speak("Testing Piper speech synthesis.")
    assert isinstance(res, SpeechSynthesisResult)
    assert res.success is True
    piper.shutdown()


def test_piper_provider_stream_speak():
    piper = PiperProvider()
    piper.initialize()
    stream = piper.stream_speak(["First sentence.", "Second sentence."])
    chunks = list(stream)
    assert len(chunks) == 2
    assert isinstance(chunks[0], bytes)
    piper.shutdown()


def test_pyttsx3_provider_speak():
    tts = PyTTSx3TTSProvider(max_chars=100)
    tts.initialize()
    res = tts.speak("Hello Jarvis test.")
    assert res.success is True
    tts.shutdown()
