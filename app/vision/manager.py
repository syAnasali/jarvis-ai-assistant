"""Vision subsystem manager acting as orchestrator and coordinator."""

from typing import Any, Dict, Optional
from app.core.logger import JarvisLogger
from app.vision.capture import PILScreenCapturer
from app.vision.clipboard import PILClipboardImageRetriever
from app.vision.interfaces import ClipboardImageRetriever, OCREngine, ScreenCapturer, VisionProvider
from app.vision.models import VisionImage, VisionResponse
from app.vision.ocr import LocalOCREngine
from app.vision.pipeline import VisionPipeline
from app.vision.providers import OllamaVisionProvider

logger = JarvisLogger.get_logger("vision_manager")


class VisionManager:
    """Orchestrates Vision Subsystem components with telemetry."""

    def __init__(
        self,
        provider: Optional[VisionProvider] = None,
        capturer: Optional[ScreenCapturer] = None,
        clipboard: Optional[ClipboardImageRetriever] = None,
        ocr: Optional[OCREngine] = None
    ) -> None:
        self.provider = provider or OllamaVisionProvider()
        self.capturer = capturer or PILScreenCapturer()
        self.clipboard = clipboard or PILClipboardImageRetriever()
        self.ocr = ocr or LocalOCREngine()
        self.pipeline = VisionPipeline(
            provider=self.provider,
            screen_capturer=self.capturer,
            clipboard_retriever=self.clipboard,
            ocr_engine=self.ocr
        )

        self.metrics: Dict[str, Any] = {
            "screen_captures": 0,
            "clipboard_reads": 0,
            "ocr_extractions": 0,
            "vision_analyses": 0,
            "failures": 0
        }
        self._is_initialized = False

    def initialize(self) -> None:
        """Initializes underlying Vision Pipeline."""
        if self._is_initialized:
            return
        logger.info("Initializing VisionManager components...")
        self.pipeline.initialize()
        self._is_initialized = True
        logger.info("VisionManager initialized successfully.")

    def analyze_screen(self, prompt: str = "Describe what is on screen.") -> VisionResponse:
        """Captures screen and returns vision response."""
        self.metrics["screen_captures"] += 1
        self.metrics["vision_analyses"] += 1
        return self.pipeline.process_fullscreen(prompt=prompt)

    def analyze_clipboard(self, prompt: str = "Describe the clipboard image.") -> VisionResponse:
        """Reads clipboard image and returns vision response."""
        self.metrics["clipboard_reads"] += 1
        self.metrics["vision_analyses"] += 1
        return self.pipeline.process_clipboard(prompt=prompt)

    def analyze_image(self, image: VisionImage, prompt: str = "Analyze this image.") -> VisionResponse:
        """Analyzes explicit image."""
        self.metrics["vision_analyses"] += 1
        return self.pipeline.process_image(image, prompt=prompt)

    def health_check(self) -> Dict[str, Any]:
        """Runs diagnostics on vision components."""
        return {
            "provider": self.provider.health_check(),
            "is_initialized": self._is_initialized,
            "metrics": self.metrics
        }

    def shutdown(self) -> None:
        """Safely shuts down vision components."""
        logger.info("Shutting down VisionManager...")
        self.pipeline.shutdown()
        self._is_initialized = False
        logger.info("VisionManager shutdown complete.")
