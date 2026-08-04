"""Diagnostic script testing full-duplex VoicePipeline execution flow."""

import sys
sys.path.insert(0, ".")

from datetime import datetime, timezone
from app.voice.models import AudioSegment, AudioFrame
from app.voice.stt import FasterWhisperSTTProvider
from app.voice.tts import PiperProvider
from app.voice.vad import EnergyBasedVAD
from app.voice.wakeword import LocalWakeWordDetector
from app.voice.pipeline import VoicePipeline


def main() -> None:
    print("==================================================")
    print("Testing Full-Duplex VoicePipeline Diagnostics")
    print("==================================================")

    stt = FasterWhisperSTTProvider(model_size="tiny")
    tts = PiperProvider()
    vad = EnergyBasedVAD()
    wakeword = LocalWakeWordDetector()

    pipeline = VoicePipeline(
        stt_provider=stt,
        tts_provider=tts,
        vad_detector=vad,
        wakeword_detector=wakeword
    )

    pipeline.initialize()
    print("PASS: VoicePipeline initialized successfully.")

    pcm_samples = b"\x00\x00" * 8000
    segment = AudioSegment(
        pcm_data=pcm_samples,
        sample_rate=16000,
        channels=1,
        sample_width=2,
        duration_seconds=0.5
    )

    res = pipeline.process_utterance(segment)
    print(f"Utterance result: {res}")
    print("PASS: Utterance processed cleanly.")

    pipeline.shutdown()
    print("PASS: VoicePipeline shutdown complete.")
    print("\nALL VOICE PIPELINE DIAGNOSTICS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
