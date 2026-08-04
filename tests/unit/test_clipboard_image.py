"""Unit tests for PILClipboardImageRetriever."""

import pytest
from app.vision.clipboard import PILClipboardImageRetriever
from app.vision.models import VisionImage


def test_clipboard_image_retriever_handles_empty():
    retriever = PILClipboardImageRetriever()
    img = retriever.get_clipboard_image()
    # Should either return a valid VisionImage or None cleanly without unhandled exceptions
    assert img is None or isinstance(img, VisionImage)
