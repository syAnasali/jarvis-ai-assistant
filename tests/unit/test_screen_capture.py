"""Unit tests for PILScreenCapturer and screen capture mechanisms."""

import pytest
from app.vision.capture import PILScreenCapturer, ScreenCaptureError
from app.vision.models import VisionImage


def test_pil_screen_capturer_fullscreen():
    capturer = PILScreenCapturer()
    img = capturer.capture_fullscreen()
    assert isinstance(img, VisionImage)
    assert img.source == "fullscreen"
    assert img.metadata.width > 0
    assert img.metadata.height > 0
    assert len(img.image_bytes) > 0


def test_pil_screen_capturer_active_window():
    capturer = PILScreenCapturer()
    img = capturer.capture_active_window()
    assert isinstance(img, VisionImage)
    assert img.source == "active_window"
    assert len(img.image_bytes) > 0


def test_pil_screen_capturer_region():
    capturer = PILScreenCapturer()
    img = capturer.capture_region(x=0, y=0, width=300, height=200)
    assert isinstance(img, VisionImage)
    assert img.source == "region"
    assert img.metadata.width == 300
    assert img.metadata.height == 200

    with pytest.raises(ScreenCaptureError):
        capturer.capture_region(x=-1, y=0, width=300, height=200)
