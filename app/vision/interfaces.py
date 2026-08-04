"""Abstract base interface contracts for the Vision Subsystem."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generator, Optional
from app.vision.models import OCRResult, VisionImage, VisionRequest, VisionResponse


class VisionProvider(ABC):
    """Abstract interface for local multimodal vision language models."""

    @abstractmethod
    def initialize(self) -> None:
        """Initializes model resources and provider connections."""
        pass

    @abstractmethod
    def analyze(self, request: VisionRequest) -> VisionResponse:
        """Analyzes the image payload and returns a structured VisionResponse.

        Args:
            request: The VisionRequest object.

        Returns:
            VisionResponse: Analytical visual description and structured metadata.
        """
        pass

    @abstractmethod
    def stream_analyze(self, request: VisionRequest) -> Generator[str, None, None]:
        """Streams visual analysis text fragments token by token.

        Args:
            request: The VisionRequest object.

        Yields:
            str: Token fragments.
        """
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Retrieves provider diagnostic parameters and availability status."""
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Safely releases model resources."""
        pass


class ScreenCapturer(ABC):
    """Abstract interface for capturing screen images."""

    @abstractmethod
    def capture_fullscreen(self, monitor_index: int = 0) -> VisionImage:
        """Captures full display screen."""
        pass

    @abstractmethod
    def capture_active_window(self) -> VisionImage:
        """Captures the currently active foreground window."""
        pass

    @abstractmethod
    def capture_region(self, x: int, y: int, width: int, height: int) -> VisionImage:
        """Captures a specific bounding box region of the screen."""
        pass


class ClipboardImageRetriever(ABC):
    """Abstract interface for retrieving images from the system clipboard."""

    @abstractmethod
    def get_clipboard_image(self) -> Optional[VisionImage]:
        """Retrieves an image from the clipboard, or None if no image is present."""
        pass


class OCREngine(ABC):
    """Abstract interface for optical character recognition (OCR)."""

    @abstractmethod
    def extract_text(self, image: VisionImage) -> OCRResult:
        """Extracts text and text regions from an image.

        Args:
            image: The target VisionImage.

        Returns:
            OCRResult: Extracted text blocks and confidence scores.
        """
        pass
