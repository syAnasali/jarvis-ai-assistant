"""Diagnostic script testing VoiceSession state machine and metrics."""

import sys
sys.path.insert(0, ".")

from app.voice.models import VoiceState
from app.voice.session import VoiceSession


def main() -> None:
    print("==================================================")
    print("Testing VoiceSession Tracker Diagnostics")
    print("==================================================")

    session = VoiceSession()
    print(f"Session Initialized: id={session.session_id}, state={session.state.value}")

    session.transition_to(VoiceState.LISTENING)
    assert session.state == VoiceState.LISTENING

    session.transition_to(VoiceState.PROCESSING)
    session.record_utterance(2.5)

    session.transition_to(VoiceState.INTERRUPTED, reason="User spoken barge-in")
    assert session.interruption_count == 1

    metrics = session.get_metrics()
    print(f"Session Metrics: {metrics}")
    assert metrics["utterance_count"] == 1
    assert metrics["interruption_count"] == 1
    print("PASS: VoiceSession state tracking and metrics verified.")

    print("\nALL VOICE SESSION DIAGNOSTICS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
