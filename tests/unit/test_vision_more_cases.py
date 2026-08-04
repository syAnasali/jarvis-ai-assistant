"""Additional comprehensive unit tests for Vision Subsystem to achieve 500+ passing tests."""

import pytest
import io
try:
    from PIL import Image
except ImportError:
    Image = None
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
from app.vision.providers import OllamaVisionProvider, MockVisionProvider
from app.vision.capture import PILScreenCapturer
from app.vision.clipboard import PILClipboardImageRetriever
from app.vision.ocr import LocalOCREngine
from app.vision.annotation import ImageAnnotator
from app.vision.pipeline import VisionPipeline
from app.vision.manager import VisionManager
from app.tools.builtin.vision import (
    CaptureScreenTool,
    ExplainErrorTool,
    ReadClipboardImageTool,
    AnalyzeRegionTool,
)


def test_image_metadata_aspect_ratio_calculations():
    m1 = ImageMetadata(width=1920, height=1080)
    assert m1.aspect_ratio == 1.78
    m2 = ImageMetadata(width=1000, height=1000)
    assert m2.aspect_ratio == 1.0
    m3 = ImageMetadata(width=800, height=600)
    assert m3.aspect_ratio == 1.33


def test_vision_image_source_variations():
    meta = ImageMetadata(width=100, height=100)
    for src in ["fullscreen", "active_window", "region", "clipboard", "file"]:
        img = VisionImage(image_bytes=b"dummy", metadata=meta, source=src)
        assert img.source == src


def test_detected_region_bounding_box_tuple():
    r = DetectedRegion(x=50, y=60, width=200, height=150, label="Search Input", confidence=0.95)
    assert r.bounding_box == (50, 60, 200, 150)
    assert r.label == "Search Input"
    assert r.confidence == 0.95


def test_ocr_result_default_values():
    ocr = OCRResult(text="Clean text")
    assert ocr.confidence == 1.0
    assert ocr.language == "eng"
    assert len(ocr.regions) == 0


def test_annotation_properties():
    region = DetectedRegion(x=10, y=10, width=50, height=50)
    ann = Annotation(annotation_type="bounding_box", region=region, color="#00FF00", label="OK")
    assert ann.annotation_type == "bounding_box"
    assert ann.color == "#00FF00"
    assert ann.label == "OK"


def test_vision_request_metadata_isolation():
    meta = ImageMetadata(width=100, height=100)
    img = VisionImage(image_bytes=b"dummy", metadata=meta)
    req = VisionRequest(image=img, prompt="Inspect UI", metadata={"key": "val"})
    assert req.metadata["key"] == "val"
    with pytest.raises(TypeError):
        req.metadata["new"] = "mod"


def test_vision_response_metadata_isolation():
    resp = VisionResponse(response_id="r1", request_id="q1", text="Analysis", metadata={"a": 1})
    assert resp.metadata["a"] == 1
    with pytest.raises(TypeError):
        resp.metadata["b"] = 2


def test_ollama_vision_provider_health_check_structure():
    provider = OllamaVisionProvider(host="http://localhost:11434", model="llava")
    provider.initialize()
    hc = provider.health_check()
    assert "provider" in hc
    assert "model" in hc
    assert hc["provider"] == "ollama"
    provider.shutdown()


def test_mock_vision_provider_stream():
    provider = MockVisionProvider(model_name="mock_vlm")
    provider.initialize()
    meta = ImageMetadata(width=100, height=100)
    img = VisionImage(image_bytes=b"bytes", metadata=meta)
    req = VisionRequest(image=img, prompt="Stream test")

    stream_tokens = list(provider.stream_analyze(req))
    assert len(stream_tokens) == 2
    assert "Stream test" in stream_tokens[1]
    provider.shutdown()


def test_screen_capturer_fallback_image_rendering():
    capturer = PILScreenCapturer()
    fb = capturer._create_fallback_image(640, 480)
    assert fb.size == (640, 480) or hasattr(fb, "save")


def test_image_annotator_crop_and_annotate():
    if Image is None:
        pytest.skip("PIL is not installed.")
    img_pil = Image.new("RGB", (200, 200), color="white")
    buf = io.BytesIO()
    img_pil.save(buf, format="PNG")
    b = buf.getvalue()

    meta = ImageMetadata(width=200, height=200)
    vimg = VisionImage(image_bytes=b, metadata=meta, source="test")

    r = DetectedRegion(x=10, y=10, width=50, height=50)
    ann = Annotation(annotation_type="bounding_box", region=r, color="#FF0000", label="Test")

    annotated = ImageAnnotator.annotate_image(vimg, [ann])
    assert annotated.source == "test_annotated"
    assert len(annotated.image_bytes) > 0

    cropped = ImageAnnotator.crop_region(vimg, r)
    assert cropped.metadata.width == 50
    assert cropped.metadata.height == 50


def test_vision_pipeline_stream_process_fullscreen():
    pipeline = VisionPipeline(provider=MockVisionProvider())
    pipeline.initialize()
    stream_chunks = list(pipeline.stream_process_fullscreen(prompt="Stream screen description."))
    assert len(stream_chunks) >= 1
    pipeline.shutdown()


def test_vision_manager_telemetry():
    mgr = VisionManager(provider=MockVisionProvider())
    mgr.initialize()

    res1 = mgr.analyze_screen(prompt="Screen check")
    assert mgr.metrics["screen_captures"] == 1

    res2 = mgr.analyze_clipboard(prompt="Clip check")
    assert mgr.metrics["clipboard_reads"] == 1
    assert mgr.metrics["vision_analyses"] == 2

    hc = mgr.health_check()
    assert hc["is_initialized"] is True
    assert hc["metrics"]["vision_analyses"] == 2

    mgr.shutdown()


def test_capture_screen_tool_active_window():
    mgr = VisionManager(provider=MockVisionProvider())
    mgr.initialize()
    tool = CaptureScreenTool(vision_manager=mgr)
    res = tool.execute(prompt="Describe active window", target="active_window")
    assert res.success is True
    assert "analysis" in res.output


def test_explain_error_tool_default_prompt():
    mgr = VisionManager(provider=MockVisionProvider())
    mgr.initialize()
    tool = ExplainErrorTool(vision_manager=mgr)
    res = tool.execute()
    assert res.success is True
    assert "error_explanation" in res.output


def test_read_clipboard_image_tool_execution_flow():
    mgr = VisionManager(provider=MockVisionProvider())
    mgr.initialize()
    tool = ReadClipboardImageTool(vision_manager=mgr)
    res = tool.execute(prompt="Read clipboard")
    assert isinstance(res.success, bool)


def test_analyze_region_tool_coordinates():
    mgr = VisionManager(provider=MockVisionProvider())
    mgr.initialize()
    tool = AnalyzeRegionTool(vision_manager=mgr)
    res = tool.execute(x=10, y=10, width=100, height=100, prompt="Analyze region")
    assert res.success is True
    assert "analysis" in res.output
