"""Faster-whisper based Speech-to-Text provider implementation."""

import sys
import gc
import time
from typing import Any, Dict, Optional
import numpy as np

from app.core.exceptions import VoiceError
from app.voice.interfaces import SpeechToTextProvider
from app.voice.models import AudioSegment, TranscriptionResult
from app.core.logger import JarvisLogger

logger = JarvisLogger.get_logger("stt")


class STTInitializationError(VoiceError):
    """Raised when the Speech-to-Text model fails to initialize."""
    pass


class FasterWhisperSTTProvider(SpeechToTextProvider):
    """Speech-to-Text provider using faster-whisper local model."""

    def __init__(
        self,
        model_size: str = "tiny",
        device: str = "auto",
        compute_type: str = "auto",
        language: Optional[str] = None
    ) -> None:
        """Initializes settings but does not load model weights (lazy loading)."""
        self._model_size = model_size
        self._requested_device = device
        self._requested_compute_type = compute_type
        self._language = language

        # Loaded attributes
        self._model: Optional[Any] = None
        self._resolved_device: str = "cpu"
        self._resolved_compute_type: str = "int8"
        self._is_initialized: bool = False

    def initialize(self) -> None:
        """Loads faster-whisper model into memory once."""
        if self._is_initialized:
            return

        logger.info("Initializing FasterWhisper STT model...")
        start_time = time.perf_counter()

        try:
            from faster_whisper import WhisperModel
            import ctranslate2
        except ImportError as e:
            raise STTInitializationError(
                f"Required dependencies for faster-whisper are missing: {e}. Please ensure it is installed."
            ) from e

        # Determine device (cuda or cpu)
        cuda_available = False
        try:
            cuda_available = ctranslate2.get_cuda_device_count() > 0
        except Exception:
            pass

        device = self._requested_device.lower()
        if device == "auto":
            device = "cuda" if cuda_available else "cpu"
        elif device == "cuda" and not cuda_available:
            logger.warning("CUDA execution was requested but GPU count is 0. Falling back to CPU.")
            device = "cpu"

        # Determine compute type based on device
        compute_type = self._requested_compute_type
        if device == "cpu":
            # float16 is not supported on CPU in ctranslate2
            if compute_type in ("auto", "float16"):
                compute_type = "int8"
        else:
            # GPU
            if compute_type == "auto":
                compute_type = "float16"

        self._resolved_device = device
        self._resolved_compute_type = compute_type

        logger.info(
            f"Loading WhisperModel '{self._model_size}' on resolved device='{self._resolved_device}' "
            f"with compute_type='{self._resolved_compute_type}'"
        )

        try:
            self._model = WhisperModel(
                self._model_size,
                device=self._resolved_device,
                compute_type=self._resolved_compute_type
            )
            self._is_initialized = True
            dur = (time.perf_counter() - start_time) * 1000.0
            logger.info(f"FasterWhisper STT model loaded successfully in {dur:.2f}ms.")
        except Exception as e:
            self._model = None
            self._is_initialized = False
            raise STTInitializationError(
                f"Failed to load WhisperModel '{self._model_size}' on '{self._resolved_device}': {e}"
            ) from e

    def transcribe(self, segment: AudioSegment) -> TranscriptionResult:
        """Transcribes the given audio segment using loaded model."""
        if not self._is_initialized or self._model is None:
            raise VoiceError("SpeechToTextProvider is not initialized. Call initialize() first.")

        start_time = time.perf_counter()
        
        try:
            # Convert 16-bit PCM bytes to float32 normalized [-1.0, 1.0] numpy array
            audio_np = np.frombuffer(segment.pcm_data, dtype=np.int16).astype(np.float32) / 32768.0

            try:
                # Perform transcription
                segments, info = self._model.transcribe(
                    audio_np,
                    beam_size=5,
                    language=self._language
                )
                segments_list = list(segments)
            except RuntimeError as run_err:
                # Detect missing DLLs or CUDA runtime issues
                err_str = str(run_err).lower()
                if "cublas" in err_str or "cuda" in err_str or "cudnn" in err_str:
                    logger.warning(
                        f"CUDA execution failed due to missing libraries/runtime ({run_err}). "
                        f"Attempting fallback to CPU."
                    )
                    # Force CPU configuration and reload model
                    from faster_whisper import WhisperModel
                    self._resolved_device = "cpu"
                    self._resolved_compute_type = "int8"
                    logger.info("Reloading WhisperModel on CPU (int8)...")
                    self._model = WhisperModel(
                        self._model_size,
                        device=self._resolved_device,
                        compute_type=self._resolved_compute_type
                    )
                    # Retry once on CPU
                    segments, info = self._model.transcribe(
                        audio_np,
                        beam_size=5,
                        language=self._language
                    )
                    segments_list = list(segments)
                else:
                    raise

            text = "".join(seg.text for seg in segments_list).strip()

            # Normalize whitespace
            normalized_text = " ".join(text.split())

            # If whitespace-only transcription, produce an empty result
            if not normalized_text:
                normalized_text = ""

            dur = time.perf_counter() - start_time
            
            avg_logprob = None
            if segments_list:
                # Average logprob of segments
                avg_logprob = float(np.mean([seg.avg_logprob for seg in segments_list]))

            return TranscriptionResult(
                text=normalized_text,
                confidence=None,  # Do not fabricate confidence
                language=info.language if info else None,
                duration_seconds=dur,
                metadata={
                    "avg_logprob": avg_logprob,
                    "language_probability": info.language_probability if info else None,
                    "device": self._resolved_device,
                    "compute_type": self._resolved_compute_type
                }
            )

        except Exception as e:
            logger.error(f"Error during audio transcription: {e}")
            raise VoiceError(f"Transcription failed: {e}") from e

    def health_check(self) -> Dict[str, Any]:
        """Returns diagnostic details."""
        return {
            "provider": "faster_whisper",
            "model": self._model_size,
            "device": self._resolved_device if self._is_initialized else self._requested_device,
            "compute_type": self._resolved_compute_type if self._is_initialized else self._requested_compute_type,
            "available": self._is_initialized
        }

    def shutdown(self) -> None:
        """Idempotently shuts down model resources."""
        if not self._is_initialized:
            return

        logger.info("Shutting down FasterWhisper STT model...")
        self._model = None
        self._is_initialized = False
        # Request GC cleanup
        gc.collect()
        logger.info("FasterWhisper STT model shutdown complete.")
