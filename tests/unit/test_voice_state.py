"""Unit tests for the VoiceRuntime state transitions."""

import pytest
from unittest.mock import MagicMock

from app.core.exceptions import VoiceError
from app.voice.models import VoiceState
from app.voice.runtime import VoiceRuntime


def test_voice_state_transitions() -> None:
    manager_mock = MagicMock()
    controller_mock = MagicMock()
    runtime = VoiceRuntime(manager=manager_mock, agent_controller=controller_mock)

    # Initial state is STOPPED
    assert runtime.state == VoiceState.STOPPED

    # START transition allowed (STOPPED -> IDLE)
    runtime.start()
    assert runtime.state == VoiceState.IDLE

    # Invalid transition (IDLE -> SPEAKING directly)
    with pytest.raises(VoiceError, match="Invalid state transition"):
        runtime._transition_to(VoiceState.SPEAKING)

    # Valid transition (IDLE -> LISTENING)
    runtime._transition_to(VoiceState.LISTENING)
    assert runtime.state == VoiceState.LISTENING

    # Valid transition (LISTENING -> TRANSCRIBING)
    runtime._transition_to(VoiceState.TRANSCRIBING)
    assert runtime.state == VoiceState.TRANSCRIBING

    # Valid transition (TRANSCRIBING -> PROCESSING)
    runtime._transition_to(VoiceState.PROCESSING)
    assert runtime.state == VoiceState.PROCESSING

    # Valid transition (PROCESSING -> SPEAKING)
    runtime._transition_to(VoiceState.SPEAKING)
    assert runtime.state == VoiceState.SPEAKING

    # Valid transition (SPEAKING -> IDLE)
    runtime._transition_to(VoiceState.IDLE)
    assert runtime.state == VoiceState.IDLE


def test_voice_state_transition_wildcards() -> None:
    manager_mock = MagicMock()
    controller_mock = MagicMock()
    runtime = VoiceRuntime(manager=manager_mock, agent_controller=controller_mock)

    runtime.start()
    runtime._transition_to(VoiceState.LISTENING)

    # Can transition to ERROR from anywhere
    runtime._transition_to(VoiceState.ERROR)
    assert runtime.state == VoiceState.ERROR

    # Can transition to STOPPED from anywhere
    runtime._transition_to(VoiceState.STOPPED)
    assert runtime.state == VoiceState.STOPPED
