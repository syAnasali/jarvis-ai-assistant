"""Diagnostic script for local Text-to-Speech synthesis playback."""

import time
from app.voice.tts import PyTTSx3TTSProvider

def main() -> None:
    print("=== Local Text-to-Speech Diagnostic ===")
    
    # Initialize pyttsx3 provider
    provider = PyTTSx3TTSProvider(rate=175)
    
    print("\nInitializing TTS Provider...")
    start_load = time.perf_counter()
    provider.initialize()
    load_dur = time.perf_counter() - start_load
    print(f"TTS engine initialized in {load_dur * 1000.0:.2f}ms.")
    
    # Show diagnostics
    diag = provider.health_check()
    print("\nHealth Status:")
    for k, v in diag.items():
        print(f" - {k}: {v}")

    # Text to speak
    phrase = "Hello Anas. Jarvis voice runtime is working."
    print(f"\nSpeaking phrase: '{phrase}'")
    
    start_speak = time.perf_counter()
    res = provider.speak(phrase)
    speak_dur = time.perf_counter() - start_speak
    
    print("\nSpeech synthesis result:")
    print(f" - Success:  {res.success}")
    print(f" - Duration: {res.duration_seconds} seconds")
    print(f" - Blocked time: {speak_dur:.2f} seconds")
    
    provider.shutdown()
    print("\nDIAGNOSTIC STATUS: PASS")

if __name__ == "__main__":
    main()
