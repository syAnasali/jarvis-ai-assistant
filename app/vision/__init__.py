"""Vision Subsystem package exports."""

from app.vision.models import (
    ImageMetadata,
    VisionImage,
    DetectedRegion,
    OCRResult,
    Annotation,
    VisionRequest,
    VisionResponse,
)
from app.vision.interfaces import (
    VisionProvider,
    ScreenCapturer,
    ClipboardImageRetriever,
    OCREngine,
)
from app.vision.providers import OllamaVisionProvider, MockVisionProvider, VisionProviderError
from app.vision.capture import PILScreenCapturer, ScreenCaptureError
from app.vision.clipboard import PILClipboardImageRetriever
from app.vision.ocr import LocalOCREngine
from app.vision.annotation import ImageAnnotator
from app.vision.pipeline import VisionPipeline
from app.vision.manager import VisionManager

__all__ = [
    "ImageMetadata",
    "VisionImage",
    "DetectedRegion",
    "OCRResult",
    "Annotation",
    "VisionRequest",
    "VisionResponse",
    "VisionProvider",
    "ScreenCapturer",
    "ClipboardImageRetriever",
    "OCREngine",
    "OllamaVisionProvider",
    "MockVisionProvider",
    "VisionProviderError",
    "PILScreenCapturer",
    "ScreenCaptureError",
    "PILClipboardImageRetriever",
    "LocalOCREngine",
    "ImageAnnotator",
    "VisionPipeline",
    "VisionManager",
]
