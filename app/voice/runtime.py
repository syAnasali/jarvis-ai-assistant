"""Stateful Voice Runtime orchestrating the push-to-talk loop with AgentController."""

import time
from typing import Any, Dict, Optional
from datetime import datetime, timezone

from app.core.exceptions import VoiceError
from app.voice.models import VoiceState
from app.voice.manager import VoiceManager
from app.utils.id_generator import generate_request_id
from app.core.logger import JarvisLogger

logger = JarvisLogger.get_logger("voice_runtime")


class VoiceRuntime:
    """Manages push-to-talk voice loops, transitions, and AgentController coupling."""

    def __init__(self, manager: VoiceManager, agent_controller: Any) -> None:
        self.manager = manager
        self.agent_controller = agent_controller
        self._state: VoiceState = VoiceState.STOPPED

        # Valid transitions mapping: current_state -> set of allowed next_states
        self._allowed_transitions: Dict[VoiceState, set] = {
            VoiceState.STOPPED: {VoiceState.IDLE},
            VoiceState.IDLE: {VoiceState.LISTENING, VoiceState.STOPPED, VoiceState.ERROR},
            VoiceState.LISTENING: {VoiceState.TRANSCRIBING, VoiceState.IDLE, VoiceState.ERROR},
            VoiceState.TRANSCRIBING: {VoiceState.PROCESSING, VoiceState.IDLE, VoiceState.ERROR},
            VoiceState.PROCESSING: {VoiceState.SPEAKING, VoiceState.WAITING_APPROVAL, VoiceState.IDLE, VoiceState.ERROR},
            VoiceState.SPEAKING: {VoiceState.WAITING_APPROVAL, VoiceState.IDLE, VoiceState.ERROR},
            VoiceState.WAITING_APPROVAL: {VoiceState.IDLE, VoiceState.ERROR},
            VoiceState.ERROR: {VoiceState.IDLE, VoiceState.STOPPED}
        }

    @property
    def state(self) -> VoiceState:
        """Exposes the current state for UI integrations."""
        return self._state

    def _transition_to(self, new_state: VoiceState) -> None:
        """Transitions state, validating transition rules."""
        if new_state == self._state:
            return

        # Special wildcard-like transition logic: we can always transition to ERROR or STOPPED
        allowed = self._allowed_transitions.get(self._state, set())
        if new_state not in allowed and new_state not in (VoiceState.ERROR, VoiceState.STOPPED):
            msg = f"Invalid state transition from {self._state.name} to {new_state.name}"
            logger.error(msg)
            raise VoiceError(msg)

        logger.info(f"Voice state transition: {self._state.name} -> {new_state.name}")
        self._state = new_state

    def start(self) -> None:
        """Starts voice runtime system."""
        if self._state != VoiceState.STOPPED:
            logger.warning("VoiceRuntime is already started.")
            return

        self._transition_to(VoiceState.IDLE)
        self.manager.initialize()

    def listen_and_process(self, device_id: Optional[int] = None) -> None:
        """Requests one spoken utterance, processes it, and speaks response."""
        if self._state != VoiceState.IDLE:
            raise VoiceError(f"Cannot capture voice while runtime is in state: {self._state.name}")

        self._transition_to(VoiceState.LISTENING)

        # 1. Listen and transcribe
        status, result = self.manager.listen_once(device_id=device_id)

        if status == "TIMEOUT":
            self._transition_to(VoiceState.IDLE)
            print("[No speech detected: listening timed out]")
            return

        if status == "NO_SPEECH":
            self._transition_to(VoiceState.IDLE)
            print("[No valid speech captured]")
            return

        if status == "TRANSCRIPTION_EMPTY":
            self._transition_to(VoiceState.IDLE)
            print("[Empty transcription: no request generated]")
            return

        if status == "ERROR" or not result:
            self._transition_to(VoiceState.ERROR)
            self._transition_to(VoiceState.IDLE)
            print("[Voice capture or transcription error encountered]")
            return

        # 2. Process Transcription
        self._transition_to(VoiceState.TRANSCRIBING)
        self._transition_to(VoiceState.PROCESSING)

        print(f"\nYou said: {result.text}")

        # Create Agent Request (source='voice')
        from app.agent.models import AgentRequest
        request = AgentRequest(
            request_id=generate_request_id(),
            text=result.text,
            source="voice",
            timestamp=datetime.now(timezone.utc),
            metadata={}
        )

        start_agent = time.perf_counter()
        try:
            # Process via authoritative AgentController
            response = self.agent_controller.process_request(request)
            
            agent_duration_ms = (time.perf_counter() - start_agent) * 1000.0
            self.manager.metrics["total_agent_processing_ms"] += agent_duration_ms

            # 3. Speak Response
            self._transition_to(VoiceState.SPEAKING)
            print(f"Jarvis: {response.text}\n")

            # Check if confirmation required
            if response.metadata.get("confirmation_required"):
                warning_msg = "The requested action requires confirmation. Please approve it through the current confirmation interface."
                print(f"Jarvis: {warning_msg}\n")
                
                # Speak both the original text (if non-empty) and the approval warning
                if response.text:
                    self.manager.speak(response.text)
                self.manager.speak(warning_msg)
                
                self._transition_to(VoiceState.WAITING_APPROVAL)
                self._transition_to(VoiceState.IDLE)
            else:
                self.manager.speak(response.text)
                self._transition_to(VoiceState.IDLE)

        except Exception as e:
            self._transition_to(VoiceState.ERROR)
            self._transition_to(VoiceState.IDLE)
            logger.error(f"Error processing agent voice command request: {e}")
            print(f"[Agent processing error: {e}]")

    def stop(self) -> None:
        """Shuts down the voice runtime."""
        if self._state == VoiceState.STOPPED:
            return

        self._transition_to(VoiceState.STOPPED)
        self.manager.shutdown()
