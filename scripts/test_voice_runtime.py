"""Diagnostic script to verify E2E VoiceRuntime integration with mock OllamaProvider."""

import time
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app.core.application import Application
from app.voice.runtime import VoiceRuntime
from app.voice.manager import VoiceManager
from app.voice.models import TranscriptionResult
from app.ai.providers.ollama import OllamaProvider
from app.ai.models import GenerationResult, GenerationMetrics

def main() -> None:
    print("=== E2E Voice Runtime Integration Diagnostic ===")
    
    app = Application()
    try:
        # Patch OllamaProvider.initialize and OllamaProvider.generate to bypass real connection
        with patch.object(OllamaProvider, "initialize", lambda self: setattr(self, "_client", MagicMock())):
            # Mock generate response
            mock_result = GenerationResult(
                raw_response={
                    "message": {
                        "content": "The disk usage on drive C is 40% used (40 GB free of 100 GB)."
                    }
                },
                metrics=GenerationMetrics(
                    provider="ollama",
                    model="qwen3",
                    total_duration_ms=100.0
                )
            )
            
            with patch.object(OllamaProvider, "generate", return_value=mock_result):
                app.initialize()
                
                # Initialize LLM and Agent controller as in normal run
                app._initialize_llm()
                app._initialize_agent()
                
                # Lazy bootstrap voice components
                from app.voice.capture import SoundDeviceAudioCapture
                from app.voice.vad import EnergyBasedVAD
                from app.voice.stt import FasterWhisperSTTProvider
                from app.voice.tts import PyTTSx3TTSProvider
                
                capture = SoundDeviceAudioCapture()
                vad = EnergyBasedVAD()
                stt = FasterWhisperSTTProvider(model_size="tiny", device="auto")
                tts = PyTTSx3TTSProvider()
                
                manager = VoiceManager(capture=capture, vad=vad, stt=stt, tts=tts)
                controller = app.container.get("controller")
                runtime = VoiceRuntime(manager=manager, agent_controller=controller)
                
                app.container.register("voice_manager", manager)
                app.container.register("voice_runtime", runtime)
                
                # Mock only the listen_once step to bypass microphone and speak a preset prompt
                preset_prompt = "what is the disk usage"
                print(f"\n[Simulating user speech input: '{preset_prompt}']")
                
                # Set up mock transcription result
                mock_trans_result = TranscriptionResult(
                    text=preset_prompt,
                    confidence=1.0,
                    language="en",
                    duration_seconds=0.1
                )
                
                with patch.object(manager, "listen_once", return_value=("TRANSCRIBED", mock_trans_result)):
                    runtime.start()
                    
                    start_time = time.perf_counter()
                    runtime.listen_and_process()
                    dur = time.perf_counter() - start_time
                    
                    print(f"E2E Request processed and spoken in {dur:.2f} seconds.")
                    
                    # Assertions: check conversation log has the turn
                    history = controller.conversation.get_history()
                    assert len(history) >= 2
                    user_msg = history[-2]
                    assistant_msg = history[-1]
                    
                    assert user_msg.content == preset_prompt
                    assert user_msg.role.value == "user"
                    assert assistant_msg.role.value == "assistant"
                    print(f"[PASS] E2E Conversation turns verified. Assistant responded: '{assistant_msg.content}'")
                    
                    runtime.stop()
            
    except Exception as e:
        print(f"\n[FAIL] Exception during E2E voice runtime diagnostic: {e}")
        app.shutdown()
        sys.exit(1)
    finally:
        app.shutdown()
        
    print("\nDIAGNOSTIC STATUS: PASS")

if __name__ == "__main__":
    main()
