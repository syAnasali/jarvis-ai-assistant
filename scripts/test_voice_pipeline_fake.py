"""Diagnostic script verifying the voice loop with fake components and timing metrics."""

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.voice.models import AudioFrame, AudioSegment, TranscriptionResult, SpeechSynthesisResult, VoiceState
from app.voice.interfaces import AudioCapture, VoiceActivityDetector, SpeechToTextProvider, TextToSpeechProvider
from app.voice.manager import VoiceManager
from app.voice.runtime import VoiceRuntime
from app.agent.models import AgentResponse


class FakeAudioCapture(AudioCapture):
    def list_input_devices(self) -> List[Dict[str, Any]]:
        return [{"device_id": 0, "name": "Fake Mic", "is_default": True, "max_input_channels": 1}]

    def open_capture(self, device_id: Optional[int] = None) -> None:
        self.frames_sent = 0

    def read_frame(self) -> AudioFrame:
        time.sleep(0.01)  # Simulate 10ms frame read
        self.frames_sent += 1
        # Send silence (energy=0) for 10 frames, then speech (energy=200) for 10 frames, then silence
        energy = 0
        if 10 <= self.frames_sent < 20:
            energy = 200
        
        pcm = (energy).to_bytes(2, byteorder='little', signed=True) * 512
        return AudioFrame(
            pcm_data=pcm,
            sample_rate=16000,
            channels=1,
            sample_width=2,
            timestamp=datetime.now(timezone.utc)
        )

    def close_capture(self) -> None:
        pass

    def health_check(self) -> Dict[str, Any]:
        return {"available": True}


class FakeVAD(VoiceActivityDetector):
    def __init__(self) -> None:
        self.reset()

    def process_frame(self, frame: AudioFrame) -> None:
        self.calls += 1
        # Simple simulation: speech starts at call 10, ends at call 20
        if self.calls == 10:
            self.state = "SPEECH_ACTIVE"
        elif self.calls == 20:
            self.state = "COMPLETE"

    def is_speech_active(self) -> bool:
        return self.state == "SPEECH_ACTIVE"

    def has_speech_started(self) -> bool:
        return self.calls >= 10

    def has_speech_ended(self) -> bool:
        return self.state == "COMPLETE"

    def get_captured_segment(self) -> Optional[AudioSegment]:
        return AudioSegment(
            pcm_data=b"\x00" * 32000,
            sample_rate=16000,
            channels=1,
            sample_width=2,
            duration_seconds=1.0
        )

    def reset(self) -> None:
        self.state = "WAITING_FOR_SPEECH"
        self.calls = 0

    def get_state(self) -> str:
        return self.state


class FakeSTT(SpeechToTextProvider):
    def initialize(self) -> None:
        pass

    def transcribe(self, segment: AudioSegment) -> TranscriptionResult:
        # Simulate STT delay
        time.sleep(0.15)
        return TranscriptionResult(
            text="what is the weather like",
            confidence=0.98,
            language="en",
            duration_seconds=0.15
        )

    def health_check(self) -> Dict[str, Any]:
        return {"available": True}

    def shutdown(self) -> None:
        pass


class FakeTTS(TextToSpeechProvider):
    def initialize(self) -> None:
        pass

    def speak(self, text: str) -> SpeechSynthesisResult:
        # Simulate speech delay
        time.sleep(0.2)
        return SpeechSynthesisResult(success=True, duration_seconds=0.2)

    def stop(self) -> None:
        pass

    def health_check(self) -> Dict[str, Any]:
        return {"available": True}

    def shutdown(self) -> None:
        pass


class FakeAgentController:
    def process_request(self, request: Any) -> AgentResponse:
        time.sleep(0.1)  # Simulate 100ms LLM processing
        return AgentResponse(
            response_id="res_fake",
            text="The weather is sunny with a temperature of 25 degrees Celsius.",
            metadata={"confirmation_required": False}
        )


def main() -> None:
    print("=== Fake Voice Pipeline E2E Diagnostic ===")
    
    capture = FakeAudioCapture()
    vad = FakeVAD()
    stt = FakeSTT()
    tts = FakeTTS()
    
    manager = VoiceManager(capture=capture, vad=vad, stt=stt, tts=tts)
    controller = FakeAgentController()
    runtime = VoiceRuntime(manager=manager, agent_controller=controller)

    start_init = time.perf_counter()
    runtime.start()
    init_ms = (time.perf_counter() - start_init) * 1000.0
    print(f"Subsystems initialized in {init_ms:.2f}ms.")

    print("\n[Start push-to-talk sequence]")
    start_run = time.perf_counter()
    runtime.listen_and_process()
    total_ms = (time.perf_counter() - start_run) * 1000.0

    print("=== Pipeline Stage Timings ===")
    print(f"STT Transcription time: {manager.metrics['total_transcription_ms']:.2f}ms")
    print(f"Agent processing time:   {manager.metrics['total_agent_processing_ms']:.2f}ms")
    print(f"Total loop response time: {total_ms:.2f}ms")
    
    # Assert successful states
    assert manager.metrics["listen_requests"] == 1
    assert manager.metrics["speech_detected"] == 1
    assert manager.metrics["successful_transcriptions"] == 1
    assert manager.metrics["total_audio_seconds"] == 1.0
    
    runtime.stop()
    print("\nDIAGNOSTIC STATUS: PASS")


if __name__ == "__main__":
    main()
