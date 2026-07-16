"""Diagnostic script verifying voice runtime approval safety barriers."""

import sys
import time
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from app.core.application import Application
from app.voice.runtime import VoiceRuntime
from app.voice.manager import VoiceManager
from app.voice.models import TranscriptionResult, VoiceState
from app.ai.providers.ollama import OllamaProvider
from app.ai.models import GenerationResult, GenerationMetrics
from app.approval.models import PendingActionStatus

def main() -> None:
    print("=== Voice Approval Safety Diagnostic ===")
    
    app = Application()
    try:
        # Patch OllamaProvider.initialize and OllamaProvider.generate to bypass real connection
        with patch.object(OllamaProvider, "initialize", lambda self: setattr(self, "_client", MagicMock())):
            # 1. Mock response for first request "Perform the confirmation action."
            # It will return a tool call to 'type_text' (which requires confirmation)
            mock_tool_call_result = GenerationResult(
                raw_response={
                    "message": {
                        "content": "I will type text now.",
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "type_text",
                                    "arguments": {"text": "secret password"}
                                }
                            }
                        ]
                    }
                },
                metrics=GenerationMetrics(
                    provider="ollama",
                    model="qwen3",
                    total_duration_ms=50.0
                )
            )

            # 2. Mock response for second request "yes"
            # It will return a normal chat response
            mock_chat_result = GenerationResult(
                raw_response={
                    "message": {
                        "content": "You said yes, but I cannot perform the action without terminal confirmation."
                    }
                },
                metrics=GenerationMetrics(
                    provider="ollama",
                    model="qwen3",
                    total_duration_ms=50.0
                )
            )
            
            # Setup dynamic mock generator to handle memory extraction separately
            def mock_generate(self, messages, options=None, tools=None, profile=None):
                from app.ai.models import GenerationProfile
                if profile == GenerationProfile.MEMORY_EXTRACTION:
                    return GenerationResult(
                        raw_response={"message": {"content": "[]"}},
                        metrics=GenerationMetrics(provider="ollama", model="qwen3", total_duration_ms=10.0)
                    )
                if mock_generate.call_count == 0:
                    mock_generate.call_count += 1
                    return mock_tool_call_result
                return mock_chat_result
                
            mock_generate.call_count = 0
            
            with patch.object(OllamaProvider, "generate", mock_generate):
                app.initialize()
                app._initialize_llm()
                app._initialize_agent()
                
                from app.voice.capture import SoundDeviceAudioCapture
                from app.voice.vad import EnergyBasedVAD
                from app.voice.stt import FasterWhisperSTTProvider
                from app.voice.tts import PyTTSx3TTSProvider
                
                # Use fakes to keep it completely self-contained
                capture = SoundDeviceAudioCapture()
                vad = EnergyBasedVAD()
                stt = FasterWhisperSTTProvider(model_size="tiny", device="auto")
                tts = PyTTSx3TTSProvider()
                
                manager = VoiceManager(capture=capture, vad=vad, stt=stt, tts=tts)
                controller = app.container.get("controller")
                runtime = VoiceRuntime(manager=manager, agent_controller=controller)
                
                app.container.register("voice_manager", manager)
                app.container.register("voice_runtime", runtime)
                
                runtime.start()
                
                # First Turn: User says "Perform the confirmation action."
                first_prompt = "Perform the confirmation action."
                print(f"\n1. Simulating voice prompt: '{first_prompt}'")
                
                trans1 = TranscriptionResult(text=first_prompt, confidence=1.0, duration_seconds=0.1)
                
                # Mock speak to record calls
                speak_spy = MagicMock()
                with patch.object(manager, "speak", speak_spy):
                    with patch.object(manager, "listen_once", return_value=("TRANSCRIBED", trans1)):
                        # Capture state transitions
                        state_history = []
                        original_transition = runtime._transition_to
                        
                        def transition_spy(new_state):
                            state_history.append(new_state)
                            original_transition(new_state)
                            
                        with patch.object(runtime, "_transition_to", transition_spy):
                            runtime.listen_and_process()
                            
                # Verify state history includes WAITING_APPROVAL
                assert VoiceState.WAITING_APPROVAL in state_history
                print("[PASS] Voice runtime reported WAITING_APPROVAL state during suspension.")
                
                # Verify PendingAction created in DB
                approval_manager = app.container.get("approval_manager")
                pending_actions = approval_manager._repository.list_pending()
                # Find the specific action we just created
                matching_actions = [a for a in pending_actions if a.tool_name == "type_text"]
                assert len(matching_actions) >= 1, f"Expected at least 1 pending action for type_text, got {len(matching_actions)}"
                action = matching_actions[0]
                assert action.status == PendingActionStatus.PENDING, f"Expected PENDING, got {action.status}"
                print(f"[PASS] PendingAction created in DB: Tool: '{action.tool_name}', Status: '{action.status}'")
                
                # Verify warning message was spoken
                warning_spoken = False
                for call in speak_spy.call_args_list:
                    phrase = call[0][0]
                    if "requires confirmation" in phrase.lower():
                        warning_spoken = True
                assert warning_spoken is True, "Expected warning message to be spoken but it wasn't"
                print("[PASS] Warning warning was spoken by Jarvis TTS.")

                # Second Turn: User says "yes" to try to force approval
                second_prompt = "yes"
                print(f"\n2. Simulating voice prompt: '{second_prompt}'")
                
                trans2 = TranscriptionResult(text=second_prompt, confidence=1.0, duration_seconds=0.1)
                
                with patch.object(manager, "listen_once", return_value=("TRANSCRIBED", trans2)):
                    runtime.listen_and_process()
                    
                # Verify PendingAction remains unapproved
                action_after = approval_manager.get(action.action_id)
                assert action_after.status == PendingActionStatus.PENDING, f"Action status changed to {action_after.status}"
                print(f"[PASS] Action remains PENDING. Spoken 'yes' did NOT auto-approve.")
                
                runtime.stop()
                
    except Exception as e:
        print(f"\n[FAIL] Exception during approval safety diagnostic: {e}")
        app.shutdown()
        sys.exit(1)
    finally:
        app.shutdown()
        
    print("\nDIAGNOSTIC STATUS: PASS")

if __name__ == "__main__":
    main()
