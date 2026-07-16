"""Voice Subsystem Manager acting as orchestrator and coordinator."""

import time
from typing import Any, Dict, Optional, Tuple

from app.core.exceptions import VoiceError
from app.voice.interfaces import AudioCapture, VoiceActivityDetector, SpeechToTextProvider, TextToSpeechProvider
from app.voice.models import AudioSegment, TranscriptionResult, SpeechSynthesisResult
from app.core.logger import JarvisLogger

logger = JarvisLogger.get_logger("voice_manager")


class VoiceManager:
    """Orchestrates audio capture, VAD, STT, and TTS components with metrics tracking."""

    def __init__(
        self,
        capture: AudioCapture,
        vad: VoiceActivityDetector,
        stt: SpeechToTextProvider,
        tts: TextToSpeechProvider
    ) -> None:
        self.capture = capture
        self.vad = vad
        self.stt = stt
        self.tts = tts

        # Metrics tracking
        self.metrics: Dict[str, Any] = {
            "listen_requests": 0,
            "speech_detected": 0,
            "no_speech_count": 0,
            "listen_timeouts": 0,
            "successful_transcriptions": 0,
            "empty_transcriptions": 0,
            "stt_failures": 0,
            "tts_requests": 0,
            "tts_failures": 0,
            "total_audio_seconds": 0.0,
            "total_transcription_ms": 0.0,
            "total_agent_processing_ms": 0.0
        }

        self._is_initialized = False

    def initialize(self) -> None:
        """Initializes underlying engines (STT and TTS)."""
        if self._is_initialized:
            return

        logger.info("Initializing VoiceManager components...")
        self.stt.initialize()
        self.tts.initialize()
        self._is_initialized = True
        logger.info("VoiceManager successfully initialized.")

    def listen_once(self, device_id: Optional[int] = None) -> Tuple[str, Optional[TranscriptionResult]]:
        """Captures a single utterance from the microphone and transcribes it.

        Args:
            device_id: Optional input device ID.

        Returns:
            Tuple[str, Optional[TranscriptionResult]]:
                - Status string: 'TRANSCRIBED', 'NO_SPEECH', 'TIMEOUT', 'TRANSCRIPTION_EMPTY', 'ERROR'
                - TranscriptionResult: The result details, if transcription was attempted.
        """
        self.metrics["listen_requests"] += 1
        logger.info("Starting listen_once capture sequence.")
        
        try:
            # 1. Open microphone
            self.capture.open_capture(device_id=device_id)
            self.vad.reset()
        except Exception as e:
            logger.error(f"Failed to open audio capture: {e}")
            self.capture.close_capture()
            return "ERROR", None

        # 2. Main recording loop driven by VAD state
        try:
            while True:
                # Read a frame (blocks inside capture)
                frame = self.capture.read_frame()
                
                # Process VAD
                self.vad.process_frame(frame)
                state = self.vad.get_state()

                if state in ("COMPLETE", "TIMEOUT", "ERROR"):
                    break
        except Exception as e:
            logger.error(f"Error during audio frame streaming: {e}")
            self.capture.close_capture()
            return "ERROR", None
        finally:
            # Always close microphone capture immediately after VAD completes
            self.capture.close_capture()

        # 3. Handle final VAD state
        final_state = self.vad.get_state()
        
        if final_state == "TIMEOUT":
            self.metrics["listen_timeouts"] += 1
            logger.info("Listening session timed out: no speech detected.")
            return "TIMEOUT", None

        if final_state == "ERROR":
            logger.error("VAD transitioned to ERROR state.")
            return "ERROR", None

        # 4. Extract and transcribe audio
        segment = self.vad.get_captured_segment()
        if not segment:
            self.metrics["no_speech_count"] += 1
            logger.info("No valid speech segment was captured.")
            return "NO_SPEECH", None

        self.metrics["speech_detected"] += 1
        self.metrics["total_audio_seconds"] += segment.duration_seconds
        logger.info(f"Utterance captured: {segment.duration_seconds:.2f}s of audio. Commencing transcription.")

        start_transcribe = time.perf_counter()
        try:
            result = self.stt.transcribe(segment)
            transcribe_ms = (time.perf_counter() - start_transcribe) * 1000.0
            self.metrics["total_transcription_ms"] += transcribe_ms

            if not result.text:
                self.metrics["empty_transcriptions"] += 1
                logger.info(f"Transcription completed (empty text) in {transcribe_ms:.1f}ms.")
                return "TRANSCRIPTION_EMPTY", result

            self.metrics["successful_transcriptions"] += 1
            logger.info(f"Transcription completed ('{result.text[:40]}...') in {transcribe_ms:.1f}ms.")
            return "TRANSCRIBED", result

        except Exception as e:
            self.metrics["stt_failures"] += 1
            logger.error(f"Speech-to-Text transcription failed: {e}")
            return "ERROR", None

    def speak(self, text: str) -> SpeechSynthesisResult:
        """Synthesizes text to speaker output."""
        self.metrics["tts_requests"] += 1
        try:
            result = self.tts.speak(text)
            if not result.success:
                self.metrics["tts_failures"] += 1
            return result
        except Exception as e:
            self.metrics["tts_failures"] += 1
            logger.error(f"Text-to-Speech synthesis failed: {e}")
            return SpeechSynthesisResult(success=False, duration_seconds=0.0, metadata={"error": str(e)})

    def stop_speaking(self) -> None:
        """Stops active speech synthesis playback."""
        try:
            self.tts.stop()
        except Exception as e:
            logger.error(f"Failed to stop TTS: {e}")

    def health_check(self) -> Dict[str, Any]:
        """Runs diagnostics on all sub-components."""
        return {
            "capture": self.capture.health_check(),
            "stt": self.stt.health_check(),
            "tts": self.tts.health_check(),
            "is_initialized": self._is_initialized
        }

    def shutdown(self) -> None:
        """Idempotently releases resources."""
        logger.info("Shutting down VoiceManager...")
        try:
            self.capture.close_capture()
        except Exception:
            pass

        try:
            self.stt.shutdown()
        except Exception:
            pass

        try:
            self.tts.shutdown()
        except Exception:
            pass

        self._is_initialized = False
        logger.info("VoiceManager shutdown complete.")
