"""Diagnostic script testing screen capture service."""

import sys
sys.path.insert(0, ".")

from app.vision.capture import PILScreenCapturer


def main() -> None:
    print("==================================================")
    print("Testing Screen Capture Diagnostics")
    print("==================================================")

    capturer = PILScreenCapturer()

    full = capturer.capture_fullscreen()
    print(f"Fullscreen Capture: source={full.source}, dimensions={full.metadata.width}x{full.metadata.height}")
    assert full.image_bytes is not None
    assert full.metadata.width > 0
    print("PASS: Fullscreen capture verified.")

    win = capturer.capture_active_window()
    print(f"Active Window Capture: source={win.source}, dimensions={win.metadata.width}x{win.metadata.height}")
    assert win.image_bytes is not None
    print("PASS: Active window capture verified.")

    reg = capturer.capture_region(x=0, y=0, width=400, height=300)
    print(f"Region Capture: source={reg.source}, dimensions={reg.metadata.width}x{reg.metadata.height}")
    assert reg.metadata.width == 400
    assert reg.metadata.height == 300
    print("PASS: Region capture verified.")

    print("\nALL SCREEN CAPTURE DIAGNOSTICS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
