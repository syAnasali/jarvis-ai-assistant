"""Unit tests for LocalOCREngine."""

import pytest
from app.vision.models import ImageMetadata, VisionImage, OCRResult
from app.vision.ocr import LocalOCREngine


def test_local_ocr_engine_extraction():
    ocr = LocalOCREngine(language="eng")
    meta = ImageMetadata(width=200, height=100)
    image = VisionImage(image_bytes=b"png_dummy_bytes", metadata=meta, source="ocr_test")

    res = ocr.extract_text(image)
    assert isinstance(res, OCRResult)
    assert res.text != ""
    assert res.language == "eng"
    assert len(res.regions) >= 1
