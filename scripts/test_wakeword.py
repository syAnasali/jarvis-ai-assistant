"""Diagnostic script testing WakeWordDetector mode configurations."""

import sys
sys.path.insert(0, ".")

from datetime import datetime, timezone
from app.voice.models import AudioFrame
from app.voice.wakeword import LocalWakeWordDetector, WakeWordMode


def main() -> None:
    print("==================================================")
    print("Testing WakeWordDetector Diagnostics")
    print("==================================================")

    detector = LocalWakeWordDetector(wake_word="Hey Jarvis", mode=WakeWordMode.PUSH_TO_TALK)
    detector.initialize()

    frame = AudioFrame(
        pcm_data=b"\x00\x00" * 160,
        sample_rate=16000,
        channels=1,
        sample_width=2,
        timestamp=datetime.now(timezone.utc)
    )

    detected = detector.process_frame(frame)
    print(f"Wake word detected in PUSH_TO_TALK: {detected}")
    assert detected is True

    detector.set_mode(WakeWordMode.DISABLED)
    detector.reset()
    assert detector.process_frame(frame) is False
    print("PASS: DISABLED mode verified.")

    detector.shutdown()
    print("PASS: WakeWordDetector shutdown complete.")
    print("\nALL WAKE WORD DIAGNOSTICS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
