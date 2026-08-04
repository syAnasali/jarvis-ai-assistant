"""Unit tests for VoiceSession tracker."""

import pytest
from app.voice.session import VoiceSession
from app.voice.models import VoiceState


def test_voice_session_initialization():
    session = VoiceSession()
    assert session.session_id.startswith("vsession_")
    assert session.state == VoiceState.IDLE
    assert session.utterance_count == 0
    assert session.interruption_count == 0
    assert session.is_active() is True


def test_voice_session_transitions_and_metrics():
    session = VoiceSession()
    session.transition_to(VoiceState.LISTENING)
    assert session.state == VoiceState.LISTENING

    session.transition_to(VoiceState.SPEAKING)
    session.transition_to(VoiceState.INTERRUPTED, reason="Barge-in")
    assert session.interruption_count == 1

    session.record_utterance(3.5)
    assert session.utterance_count == 1
    assert session.total_audio_duration_seconds == 3.5

    metrics = session.get_metrics()
    assert metrics["utterance_count"] == 1
    assert metrics["interruption_count"] == 1

    session.transition_to(VoiceState.STOPPED)
    assert session.is_active() is False
