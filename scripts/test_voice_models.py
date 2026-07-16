"""Diagnostic script to verify voice model validation and state transitions."""

import sys
from datetime import datetime, timezone
from app.voice.models import AudioFrame, AudioSegment, TranscriptionResult, SpeechSynthesisResult, VoiceState
from app.voice.runtime import VoiceRuntime
from unittest.mock import MagicMock

def run_diagnostics() -> None:
    print("=== Voice Models Diagnostic ===")
    
    # 1. Test AudioFrame creation
    try:
        frame = AudioFrame(
            pcm_data=b"\x00\x00" * 512,
            sample_rate=16000,
            channels=1,
            sample_width=2,
            timestamp=datetime.now(timezone.utc)
        )
        print("[PASS] AudioFrame successfully created.")
    except Exception as e:
        print(f"[FAIL] AudioFrame creation failed: {e}")
        sys.exit(1)

    # 2. Test AudioFrame naive timestamp rejection
    try:
        AudioFrame(
            pcm_data=b"\x00\x00" * 512,
            sample_rate=16000,
            channels=1,
            sample_width=2,
            timestamp=datetime.now()  # naive
        )
        print("[FAIL] AudioFrame accepted naive timestamp.")
        sys.exit(1)
    except ValueError as e:
        print(f"[PASS] AudioFrame successfully rejected naive timestamp: {e}")

    # 3. Test AudioSegment creation
    try:
        segment = AudioSegment(
            pcm_data=b"\x00\x00" * 16000,
            sample_rate=16000,
            channels=1,
            sample_width=2,
            duration_seconds=1.0
        )
        print("[PASS] AudioSegment successfully created.")
    except Exception as e:
        print(f"[FAIL] AudioSegment creation failed: {e}")
        sys.exit(1)

    # 4. Test state transition checking
    manager = MagicMock()
    controller = MagicMock()
    runtime = VoiceRuntime(manager=manager, agent_controller=controller)
    
    try:
        runtime.start()
        assert runtime.state == VoiceState.IDLE
        runtime._transition_to(VoiceState.LISTENING)
        assert runtime.state == VoiceState.LISTENING
        print("[PASS] Valid VoiceState transitions succeeded.")
    except Exception as e:
        print(f"[FAIL] VoiceState transition failed: {e}")
        sys.exit(1)

    try:
        runtime._transition_to(VoiceState.SPEAKING)  # Invalid (LISTENING -> SPEAKING directly)
        print("[FAIL] VoiceState allowed invalid transition.")
        sys.exit(1)
    except Exception as e:
        print(f"[PASS] VoiceState rejected invalid transition: {e}")

    print("\nDIAGNOSTIC STATUS: PASS")

if __name__ == "__main__":
    run_diagnostics()
