"""Vision Pipeline orchestrating screen/clipboard intake, OCR, and VLM analysis."""

import time
from typing import Any, Dict, Generator, Optional
from app.core.logger import JarvisLogger
from app.utils.id_generator import generate_response_id
from app.vision.annotation import ImageAnnotator
from app.vision.capture import PILScreenCapturer
from app.vision.clipboard import PILClipboardImageRetriever
from app.vision.interfaces import ClipboardImageRetriever, OCREngine, ScreenCapturer, VisionProvider
from app.vision.models import OCRResult, VisionImage, VisionRequest, VisionResponse
from app.vision.ocr import LocalOCREngine
from app.vision.providers import OllamaVisionProvider

logger = JarvisLogger.get_logger("vision_pipeline")


class VisionPipeline:
    """End-to-end vision pipeline processing visual assets."""

    def __init__(
        self,
        provider: Optional[VisionProvider] = None,
        screen_capturer: Optional[ScreenCapturer] = None,
        clipboard_retriever: Optional[ClipboardImageRetriever] = None,
        ocr_engine: Optional[OCREngine] = None
    ) -> None:
        self.provider = provider or OllamaVisionProvider()
        self.capturer = screen_capturer or PILScreenCapturer()
        self.clipboard = clipboard_retriever or PILClipboardImageRetriever()
        self.ocr = ocr_engine or LocalOCREngine()
        self._is_initialized = False

    def initialize(self) -> None:
        """Initializes underlying vision provider and OCR engine."""
        if self._is_initialized:
            return
        logger.info("Initializing VisionPipeline...")
        self.provider.initialize()
        self._is_initialized = True
        logger.info("VisionPipeline initialized successfully.")

    def process_fullscreen(self, prompt: str = "Describe what is on screen.", enable_ocr: bool = True) -> VisionResponse:
        """Captures full screen and runs visual analysis pipeline."""
        if not self._is_initialized:
            self.initialize()

        image = self.capturer.capture_fullscreen()
        return self.process_image(image, prompt=prompt, enable_ocr=enable_ocr)

    def process_active_window(self, prompt: str = "Describe active window.", enable_ocr: bool = True) -> VisionResponse:
        """Captures active foreground window and runs visual analysis pipeline."""
        if not self._is_initialized:
            self.initialize()

        image = self.capturer.capture_active_window()
        return self.process_image(image, prompt=prompt, enable_ocr=enable_ocr)

    def process_clipboard(self, prompt: str = "Describe the image in clipboard.", enable_ocr: bool = True) -> VisionResponse:
        """Retrieves clipboard image and runs visual analysis pipeline."""
        if not self._is_initialized:
            self.initialize()

        image = self.clipboard.get_clipboard_image()
        if not image:
            return VisionResponse(
                response_id=generate_response_id(),
                request_id="vreq_clip_empty",
                text="No image found in system clipboard.",
                duration_seconds=0.0,
                metadata={"status": "empty_clipboard"}
            )
        return self.process_image(image, prompt=prompt, enable_ocr=enable_ocr)

    def process_image(self, image: VisionImage, prompt: str = "Analyze this image.", enable_ocr: bool = True) -> VisionResponse:
        """Processes an explicit VisionImage through OCR and VLM provider."""
        if not self._is_initialized:
            self.initialize()

        start_time = time.perf_counter()
        ocr_result: Optional[OCRResult] = None

        # 1. OCR Extraction if requested
        if enable_ocr:
            try:
                ocr_result = self.ocr.extract_text(image)
                logger.info(f"OCR Extracted {len(ocr_result.text)} characters of text.")
            except Exception as e:
                logger.warning(f"OCR extraction failed: {e}")

        # 2. Enrich prompt with OCR text if available
        enriched_prompt = prompt
        if ocr_result and ocr_result.text:
            enriched_prompt += f"\n\n[OCR EXTRACTED TEXT FROM IMAGE]\n{ocr_result.text[:2000]}"

        # 3. Vision Provider Analysis
        req = VisionRequest(image=image, prompt=enriched_prompt, enable_ocr=enable_ocr)
        response = self.provider.analyze(req)

        dur = time.perf_counter() - start_time
        return VisionResponse(
            response_id=response.response_id,
            request_id=req.request_id,
            text=response.text,
            ocr_result=ocr_result,
            detected_regions=response.detected_regions,
            confidence=response.confidence,
            duration_seconds=dur,
            metadata=dict(response.metadata)
        )

    def stream_process_fullscreen(self, prompt: str = "Describe what is on screen.") -> Generator[str, None, None]:
        """Streams visual analysis text chunks for full screen capture."""
        if not self._is_initialized:
            self.initialize()

        image = self.capturer.capture_fullscreen()
        req = VisionRequest(image=image, prompt=prompt)
        yield from self.provider.stream_analyze(req)

    def shutdown(self) -> None:
        """Releases pipeline resources."""
        self.provider.shutdown()
        self._is_initialized = False
        logger.info("VisionPipeline shutdown complete.")
