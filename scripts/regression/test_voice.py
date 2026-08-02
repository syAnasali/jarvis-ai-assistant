import time
from unittest.mock import MagicMock
from app.voice.models import VoiceState
from app.voice.runtime import VoiceRuntime

def run_regression() -> dict:
    start_time = time.perf_counter()
    try:
        manager_mock = MagicMock()
        controller_mock = MagicMock()
        runtime = VoiceRuntime(manager=manager_mock, agent_controller=controller_mock)
        
        # Test initial state is STOPPED
        if runtime.state != VoiceState.STOPPED:
            raise ValueError(f"Expected initial state VoiceState.STOPPED, got: {runtime.state.name}")
            
        # Test start transition
        runtime.start()
        if runtime.state != VoiceState.IDLE:
            raise ValueError(f"Expected state VoiceState.IDLE, got: {runtime.state.name}")
            
        # Test transitions
        runtime._transition_to(VoiceState.LISTENING)
        if runtime.state != VoiceState.LISTENING:
            raise ValueError(f"Expected state VoiceState.LISTENING, got: {runtime.state.name}")
            
        runtime._transition_to(VoiceState.TRANSCRIBING)
        if runtime.state != VoiceState.TRANSCRIBING:
            raise ValueError(f"Expected state VoiceState.TRANSCRIBING, got: {runtime.state.name}")
            
        runtime._transition_to(VoiceState.PROCESSING)
        if runtime.state != VoiceState.PROCESSING:
            raise ValueError(f"Expected state VoiceState.PROCESSING, got: {runtime.state.name}")
            
        runtime._transition_to(VoiceState.SPEAKING)
        if runtime.state != VoiceState.SPEAKING:
            raise ValueError(f"Expected state VoiceState.SPEAKING, got: {runtime.state.name}")
            
        runtime._transition_to(VoiceState.IDLE)
        if runtime.state != VoiceState.IDLE:
            raise ValueError(f"Expected state VoiceState.IDLE, got: {runtime.state.name}")
            
        duration = time.perf_counter() - start_time
        return {
            "name": "test_voice.py",
            "status": "PASS",
            "duration": duration,
            "reason": "VoiceRuntime state transitions verified successfully."
        }
    except Exception as e:
        duration = time.perf_counter() - start_time
        return {
            "name": "test_voice.py",
            "status": "FAIL",
            "duration": duration,
            "reason": f"Voice test failed: {e}"
        }
