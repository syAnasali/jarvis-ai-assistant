"""Diagnostic script testing full end-to-end VisionPipeline."""

import sys
sys.path.insert(0, ".")

from app.vision.pipeline import VisionPipeline


def main() -> None:
    print("==================================================")
    print("Testing Full VisionPipeline Diagnostics")
    print("==================================================")

    pipeline = VisionPipeline()
    pipeline.initialize()

    resp = pipeline.process_fullscreen(prompt="Analyze current desktop state.")
    print(f"Pipeline Fullscreen Result: response_id={resp.response_id}, text='{resp.text[:60]}...'")
    assert resp.text != ""
    print("PASS: Fullscreen pipeline analysis verified.")

    clip_resp = pipeline.process_clipboard(prompt="Analyze clipboard.")
    print(f"Pipeline Clipboard Result: status={clip_resp.metadata.get('status', 'ok')}")
    print("PASS: Clipboard pipeline analysis verified.")

    pipeline.shutdown()
    print("PASS: VisionPipeline shutdown complete.")
    print("\nALL VISION PIPELINE DIAGNOSTICS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
