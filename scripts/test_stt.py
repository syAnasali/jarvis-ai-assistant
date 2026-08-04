"""Diagnostic script testing STT providers (FasterWhisperProvider)."""

import sys
sys.path.insert(0, ".")

from app.voice.models import AudioSegment, AudioFrame
from app.voice.stt import FasterWhisperSTTProvider
from datetime import datetime, timezone


def main() -> None:
    print("==================================================")
    print("Testing Speech-To-Text (STT) Provider Diagnostics")
    print("==================================================")

    stt = FasterWhisperSTTProvider(model_size="tiny")
    stt.initialize()

    health = stt.health_check()
    print(f"STT Health Check: {health}")
    assert health["available"] is True, "STT provider should be available"
    print("PASS: STT Health check verified.")

    pcm_samples = b"\x00\x00" * 16000
    segment = AudioSegment(
        pcm_data=pcm_samples,
        sample_rate=16000,
        channels=1,
        sample_width=2,
        duration_seconds=1.0
    )

    result = stt.transcribe(segment)
    print(f"Transcription Output: text='{result.text}', duration={result.duration_seconds:.2f}s")
    print("PASS: Transcription completed.")

    stt.shutdown()
    print("PASS: STT provider shutdown complete.")
    print("\nALL STT DIAGNOSTICS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
