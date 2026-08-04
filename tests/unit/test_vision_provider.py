"""Unit tests for VisionProvider implementations."""

import pytest
from app.vision.models import ImageMetadata, VisionImage, VisionRequest, VisionResponse
from app.vision.providers import OllamaVisionProvider, MockVisionProvider


def test_mock_vision_provider_lifecycle():
    provider = MockVisionProvider(model_name="mock_vlm")
    provider.initialize()
    health = provider.health_check()
    assert health["available"] is True

    meta = ImageMetadata(width=100, height=100)
    img = VisionImage(image_bytes=b"bytes", metadata=meta, source="test")
    req = VisionRequest(image=img, prompt="Analyze diagnostic test image.")

    resp = provider.analyze(req)
    assert isinstance(resp, VisionResponse)
    assert "Visual Description" in resp.text

    tokens = list(provider.stream_analyze(req))
    assert len(tokens) >= 1

    provider.shutdown()
    assert provider.health_check()["available"] is False


def test_ollama_vision_provider_fallback():
    provider = OllamaVisionProvider(host="http://invalid_localhost:9999", model="llava")
    provider.initialize()
    health = provider.health_check()
    assert health["available"] is True
    assert health["using_fallback"] is True

    meta = ImageMetadata(width=100, height=100)
    img = VisionImage(image_bytes=b"bytes", metadata=meta, source="test")
    req = VisionRequest(image=img, prompt="Analyze visual screen.")

    resp = provider.analyze(req)
    assert isinstance(resp, VisionResponse)
    assert resp.text != ""

    provider.shutdown()
