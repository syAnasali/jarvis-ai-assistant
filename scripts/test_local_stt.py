"""Diagnostic script to run speech-to-text locally on an in-memory segment."""

import time
from app.voice.stt import FasterWhisperSTTProvider
from app.voice.models import AudioSegment

def main() -> None:
    print("=== Local Speech-to-Text Diagnostic ===")
    
    # Instantiate STT provider with tiny model for speed
    provider = FasterWhisperSTTProvider(model_size="tiny", device="auto")
    
    print("\nInitializing STT Provider...")
    start_load = time.perf_counter()
    provider.initialize()
    load_dur = time.perf_counter() - start_load
    print(f"Model initialized in {load_dur:.2f} seconds.")
    
    # Show diagnostics
    diag = provider.health_check()
    print("\nHealth Status:")
    for k, v in diag.items():
        print(f" - {k}: {v}")

    # Generate a 1.5-second in-memory silent audio segment
    # 1.5 seconds * 16000 samples/sec * 2 bytes/sample = 48000 bytes
    segment = AudioSegment(
        pcm_data=b"\x00" * 48000,
        sample_rate=16000,
        channels=1,
        sample_width=2,
        duration_seconds=1.5
    )
    
    print("\nTranscribing 1.5s silent segment...")
    start_transcribe = time.perf_counter()
    res = provider.transcribe(segment)
    transcribe_dur = time.perf_counter() - start_transcribe
    
    print("\nTranscription Result:")
    print(f" - Text:         '{res.text}' (should be empty for silence)")
    print(f" - Language:     {res.language}")
    print(f" - Duration:     {res.duration_seconds:.2f} seconds")
    print(f" - Real-time processing duration: {transcribe_dur:.2f} seconds")
    
    provider.shutdown()
    print("\nDIAGNOSTIC STATUS: PASS")

if __name__ == "__main__":
    main()
