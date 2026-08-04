"""Unit tests for VisionPipeline execution using MockVisionProvider."""

import pytest
from app.vision.pipeline import VisionPipeline
from app.vision.providers import MockVisionProvider
from app.vision.models import VisionResponse


def test_vision_pipeline_fullscreen_and_clipboard():
    pipeline = VisionPipeline(provider=MockVisionProvider())
    pipeline.initialize()

    res = pipeline.process_fullscreen(prompt="Analyze full screen.", enable_ocr=True)
    assert isinstance(res, VisionResponse)
    assert res.text != ""

    clip_res = pipeline.process_clipboard(prompt="Analyze clipboard.")
    assert isinstance(clip_res, VisionResponse)

    pipeline.shutdown()
