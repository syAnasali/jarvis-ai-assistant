"""Unit tests for Vision Subsystem domain models."""

import pytest
from datetime import datetime, timezone
from app.vision.models import (
    ImageMetadata,
    VisionImage,
    DetectedRegion,
    OCRResult,
    Annotation,
    VisionRequest,
    VisionResponse,
)


def test_image_metadata_validation():
    meta = ImageMetadata(width=1920, height=1080, format="png", file_size_bytes=50000)
    assert meta.aspect_ratio == 1.78
    assert meta.width == 1920

    with pytest.raises(ValueError):
        ImageMetadata(width=0, height=1080)

    with pytest.raises(ValueError):
        ImageMetadata(width=1920, height=-5)


def test_vision_image_immutable_container():
    meta = ImageMetadata(width=100, height=100)
    img = VisionImage(
        image_bytes=b"raw_bytes",
        metadata=meta,
        source="fullscreen",
        timestamp=datetime.now(timezone.utc)
    )
    assert img.source == "fullscreen"
    assert img.image_bytes == b"raw_bytes"

    with pytest.raises(ValueError):
        VisionImage(image_bytes=b"", metadata=meta)


def test_detected_region_bounding_box():
    region = DetectedRegion(x=10, y=20, width=100, height=200, label="Button", confidence=0.9)
    assert region.bounding_box == (10, 20, 100, 200)

    with pytest.raises(ValueError):
        DetectedRegion(x=-1, y=0, width=10, height=10)


def test_ocr_result_instantiation():
    ocr = OCRResult(text="Terminal Error", confidence=0.98, language="eng")
    assert ocr.text == "Terminal Error"
    assert ocr.confidence == 0.98


def test_vision_request_response_immutable():
    meta = ImageMetadata(width=100, height=100)
    img = VisionImage(image_bytes=b"bytes", metadata=meta)
    req = VisionRequest(image=img, prompt="What is on screen?")

    assert req.prompt == "What is on screen?"
    assert req.request_id.startswith("vreq_")

    resp = VisionResponse(
        response_id="vresp_1",
        request_id=req.request_id,
        text="A desktop window."
    )
    assert resp.response_id == "vresp_1"
    assert resp.text == "A desktop window."
