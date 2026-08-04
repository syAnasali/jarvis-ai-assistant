"""Image annotation and bounding box overlay utilities."""

import io
from typing import List, Optional
from app.core.logger import JarvisLogger
from app.vision.models import Annotation, DetectedRegion, ImageMetadata, VisionImage

logger = JarvisLogger.get_logger("image_annotator")


class ImageAnnotator:
    """Draws bounding boxes, highlights, and text labels on VisionImage objects."""

    @staticmethod
    def annotate_image(image: VisionImage, annotations: List[Annotation]) -> VisionImage:
        """Applies visual annotations over an existing VisionImage."""
        if not annotations:
            return image

        logger.info(f"Applying {len(annotations)} visual annotations to VisionImage...")
        try:
            from PIL import Image, ImageDraw
            img = Image.open(io.BytesIO(image.image_bytes)).convert("RGB")
            draw = ImageDraw.Draw(img)

            for ann in annotations:
                r = ann.region
                box = [r.x, r.y, r.x + r.width, r.y + r.height]
                draw.rectangle(box, outline=ann.color, width=3)
                if ann.label:
                    draw.text((r.x + 5, max(0, r.y - 15)), ann.label, fill=ann.color)

            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            annotated_bytes = buffer.getvalue()

            meta = ImageMetadata(
                width=img.width,
                height=img.height,
                format="png",
                mode=img.mode,
                file_size_bytes=len(annotated_bytes),
                monitor_index=image.metadata.monitor_index
            )
            return VisionImage(
                image_bytes=annotated_bytes,
                metadata=meta,
                source=f"{image.source}_annotated",
                timestamp=image.timestamp
            )
        except Exception as e:
            logger.error(f"Error during image annotation: {e}")
            return image

    @staticmethod
    def crop_region(image: VisionImage, region: DetectedRegion) -> VisionImage:
        """Crops a specific sub-region out of a VisionImage."""
        logger.info(f"Cropping region {region.bounding_box} from VisionImage...")
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(image.image_bytes))
            box = (region.x, region.y, region.x + region.width, region.y + region.height)
            cropped = img.crop(box)

            buffer = io.BytesIO()
            cropped.save(buffer, format="PNG")
            cropped_bytes = buffer.getvalue()

            meta = ImageMetadata(
                width=cropped.width,
                height=cropped.height,
                format="png",
                mode=cropped.mode,
                file_size_bytes=len(cropped_bytes),
                monitor_index=image.metadata.monitor_index
            )
            return VisionImage(
                image_bytes=cropped_bytes,
                metadata=meta,
                source=f"{image.source}_cropped",
                timestamp=image.timestamp
            )
        except Exception as e:
            logger.error(f"Error cropping image region: {e}")
            return image
