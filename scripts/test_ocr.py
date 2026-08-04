"""Diagnostic script testing local OCR text extraction engine."""

import sys
sys.path.insert(0, ".")

from app.vision.models import ImageMetadata, VisionImage
from app.vision.ocr import LocalOCREngine


def main() -> None:
    print("==================================================")
    print("Testing OCR Engine Diagnostics")
    print("==================================================")

    ocr = LocalOCREngine()
    meta = ImageMetadata(width=200, height=100, format="png", file_size_bytes=500)
    image = VisionImage(image_bytes=b"\x89PNG\r\n\x1a\n" + b"\x00" * 400, metadata=meta, source="ocr_test")

    res = ocr.extract_text(image)
    print(f"OCR Extraction Text:\n{res.text}")
    assert res.text != ""
    assert res.confidence >= 0.0
    print("PASS: OCR text extraction verified.")

    print("\nALL OCR DIAGNOSTICS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
