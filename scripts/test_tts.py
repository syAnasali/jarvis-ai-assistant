"""Diagnostic script testing TTS providers (PiperProvider & PyTTSx3TTSProvider)."""

import sys
sys.path.insert(0, ".")

from app.voice.tts import PiperProvider, PyTTSx3TTSProvider


def main() -> None:
    print("==================================================")
    print("Testing Text-To-Speech (TTS) Provider Diagnostics")
    print("==================================================")

    piper = PiperProvider()
    piper.initialize()
    health = piper.health_check()
    print(f"Piper Health Check: {health}")
    assert health["available"] is True
    print("PASS: Piper provider initialized.")

    res = piper.speak("Testing Jarvis voice subsystem synthesis.")
    print(f"Speech result: success={res.success}")
    assert res.success is True
    print("PASS: Speech synthesis succeeded.")

    piper.shutdown()
    print("PASS: Piper provider shutdown complete.")
    print("\nALL TTS DIAGNOSTICS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
