"""Unit tests for the VoiceRuntime and AgentController integration."""

from unittest.mock import MagicMock, patch
import pytest

from app.core.exceptions import VoiceError
from app.agent.models import AgentResponse
from app.voice.models import TranscriptionResult, VoiceState
from app.voice.runtime import VoiceRuntime


def test_voice_runtime_successful_execution_flow() -> None:
    manager_mock = MagicMock()
    controller_mock = MagicMock()

    # Mock manager.listen_once returning transcription result
    trans_res = TranscriptionResult(text="what is the time", duration_seconds=1.0)
    manager_mock.listen_once.return_value = ("TRANSCRIBED", trans_res)

    # Mock agent controller response
    agent_res = AgentResponse(
        response_id="res_abc",
        text="The current time is 8 PM.",
        metadata={"confirmation_required": False}
    )
    controller_mock.process_request.return_value = agent_res

    runtime = VoiceRuntime(manager=manager_mock, agent_controller=controller_mock)
    runtime.start()

    # Execute voice request
    runtime.listen_and_process()

    # Verify AgentRequest structure
    controller_mock.process_request.assert_called_once()
    req_arg = controller_mock.process_request.call_args[0][0]
    
    assert req_arg.text == "what is the time"
    assert req_arg.source == "voice"
    assert req_arg.request_id is not None

    # Verify TTS called with response text
    manager_mock.speak.assert_called_once_with("The current time is 8 PM.")
    assert runtime.state == VoiceState.IDLE


def test_voice_runtime_empty_transcription_skipped() -> None:
    manager_mock = MagicMock()
    controller_mock = MagicMock()

    # Returns no speech
    manager_mock.listen_once.return_value = ("TIMEOUT", None)

    runtime = VoiceRuntime(manager=manager_mock, agent_controller=controller_mock)
    runtime.start()

    runtime.listen_and_process()

    # Agent controller and TTS should NOT be invoked
    controller_mock.process_request.assert_not_called()
    manager_mock.speak.assert_not_called()
    assert runtime.state == VoiceState.IDLE


def test_voice_runtime_overlapping_execution_blocked() -> None:
    manager_mock = MagicMock()
    controller_mock = MagicMock()

    runtime = VoiceRuntime(manager=manager_mock, agent_controller=controller_mock)
    runtime.start()

    # Manually change state to LISTENING
    runtime._transition_to(VoiceState.LISTENING)

    # Attempting to listen again should raise VoiceError
    with pytest.raises(VoiceError, match="Cannot capture voice while runtime is in state"):
        runtime.listen_and_process()


def test_voice_runtime_approval_safety_triggered() -> None:
    manager_mock = MagicMock()
    controller_mock = MagicMock()

    # Mock command requiring approval
    trans_res = TranscriptionResult(text="delete important folder", duration_seconds=1.0)
    manager_mock.listen_once.return_value = ("TRANSCRIBED", trans_res)

    # Agent controller response has confirmation_required = True
    agent_res = AgentResponse(
        response_id="res_confirm",
        text="Folder deletion requested.",
        metadata={"confirmation_required": True}
    )
    controller_mock.process_request.return_value = agent_res

    runtime = VoiceRuntime(manager=manager_mock, agent_controller=controller_mock)
    runtime.start()

    # Run loop
    runtime.listen_and_process()

    # Verify warning was spoken and NOT auto-approved
    warning_str = "The requested action requires confirmation. Please approve it through the current confirmation interface."
    
    # Manager speak should have been called twice (first with the folder deletion text, then warning)
    assert manager_mock.speak.call_count == 2
    manager_mock.speak.assert_any_call("Folder deletion requested.")
    manager_mock.speak.assert_any_call(warning_str)

    # State transitions back to IDLE
    assert runtime.state == VoiceState.IDLE
