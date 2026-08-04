"""Diagnostic script testing OllamaVisionProvider and MockVisionProvider."""

import sys
sys.path.insert(0, ".")

from app.vision.models import ImageMetadata, VisionImage, VisionRequest
from app.vision.providers import OllamaVisionProvider, MockVisionProvider


def main() -> None:
    print("==================================================")
    print("Testing Vision Provider Diagnostics")
    print("==================================================")

    provider = OllamaVisionProvider(model="llava")
    provider.initialize()

    health = provider.health_check()
    print(f"Vision Provider Health Check: {health}")
    assert health["available"] is True
    print("PASS: Provider initialized successfully.")

    meta = ImageMetadata(width=100, height=100, format="png", file_size_bytes=400)
    image = VisionImage(image_bytes=b"\x89PNG\r\n\x1a\n" + b"\x00" * 300, metadata=meta, source="test")
    request = VisionRequest(image=image, prompt="What is shown in this diagnostic test image?")

    res = provider.analyze(request)
    print(f"Analysis Output: response_id={res.response_id}, text='{res.text}'")
    assert res.text != ""
    print("PASS: Vision analysis completed.")

    provider.shutdown()
    print("PASS: Provider shutdown complete.")
    print("\nALL VISION PROVIDER DIAGNOSTICS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
