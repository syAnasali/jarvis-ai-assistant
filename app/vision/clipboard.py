"""Clipboard image retrieval implementation."""

import io
from datetime import datetime, timezone
from typing import Optional
from app.core.logger import JarvisLogger
from app.vision.interfaces import ClipboardImageRetriever
from app.vision.models import ImageMetadata, VisionImage

logger = JarvisLogger.get_logger("clipboard_image")


class PILClipboardImageRetriever(ClipboardImageRetriever):
    """Retrieves images from system clipboard using PIL ImageGrab."""

    def __init__(self, default_format: str = "png") -> None:
        self._default_format = default_format

    def get_clipboard_image(self) -> Optional[VisionImage]:
        """Retrieves image from clipboard if available."""
        logger.info("Attempting clipboard image retrieval...")
        try:
            from PIL import ImageGrab
            clip_content = ImageGrab.grabclipboard()
            if clip_content is None:
                logger.info("No image content found in system clipboard.")
                return None

            # Handle list of file paths in clipboard (e.g. copied image file)
            if isinstance(clip_content, list) and len(clip_content) > 0:
                filepath = clip_content[0]
                from PIL import Image
                img = Image.open(filepath)
            elif hasattr(clip_content, "size"):
                img = clip_content
            else:
                logger.info("Clipboard content is not a supported image object.")
                return None

            buffer = io.BytesIO()
            fmt = self._default_format.upper()
            if fmt not in ("PNG", "JPEG"):
                fmt = "PNG"

            img.save(buffer, format=fmt)
            pcm_bytes = buffer.getvalue()
            width, height = img.size

            meta = ImageMetadata(
                width=width,
                height=height,
                format=self._default_format,
                mode=img.mode,
                file_size_bytes=len(pcm_bytes)
            )
            return VisionImage(
                image_bytes=pcm_bytes,
                metadata=meta,
                source="clipboard",
                timestamp=datetime.now(timezone.utc)
            )
        except Exception as e:
            logger.warning(f"Clipboard image retrieval exception: {e}")
            return None
