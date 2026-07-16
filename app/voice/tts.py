"""Pyttsx3-based local Text-to-Speech provider implementation on Windows."""

import re
import time
from typing import Any, Dict, Optional

from app.core.exceptions import VoiceError
from app.voice.interfaces import TextToSpeechProvider
from app.voice.models import SpeechSynthesisResult
from app.core.logger import JarvisLogger

logger = JarvisLogger.get_logger("tts")


class TTSInitializationError(VoiceError):
    """Raised when the Text-to-Speech engine fails to initialize."""
    pass


def normalize_text_for_speech(text: str) -> str:
    """Strips markdown and simplifies URLs for speech synthesis."""
    if not text:
        return ""

    # 1. Remove code blocks
    text = re.sub(r'```[\s\S]*?```', ' [code block] ', text)
    
    # 2. Remove inline code backticks but keep text
    text = re.sub(r'`([^`]+)`', r'\1', text)
    
    # 3. Replace URLs with simple word "link"
    text = re.sub(r'https?://\S+', ' link ', text)
    
    # 4. Remove markdown headings markers
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    
    # 5. Remove markdown formatting markers (bold, italic, strikethrough)
    # Only remove underscores if they are not part of a word identifier (e.g. preserve execute_action)
    text = re.sub(r'(?<!\w)_(?!\w)|[\*~]+', '', text)
    
    # 6. Normalize multiple spaces and newlines to a single space
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


class PyTTSx3TTSProvider(TextToSpeechProvider):
    """Local offline TTS provider using pyttsx3 (SAPI5 on Windows)."""

    def __init__(
        self,
        voice_id: Optional[str] = None,
        rate: Optional[int] = None,
        max_chars: int = 1000
    ) -> None:
        """Initializes settings but does not instantiate the COM object yet."""
        self._voice_id = voice_id
        self._rate = rate
        self._max_chars = max_chars

        self._engine: Optional[Any] = None
        self._is_initialized: bool = False

    def initialize(self) -> None:
        """Initializes pyttsx3 engine bindings and sets properties."""
        if self._is_initialized:
            return

        logger.info("Initializing pyttsx3 TTS engine (SAPI5)...")
        start_time = time.perf_counter()

        try:
            # Initialize Windows COM in case we are in a sub-thread
            try:
                import pythoncom
                pythoncom.CoInitialize()
            except Exception:
                pass

            import pyttsx3
            
            # Use default sapi5 driver for Windows
            self._engine = pyttsx3.init(driverName="sapi5")
            
            # Apply configured rate
            if self._rate is not None:
                self._engine.setProperty('rate', self._rate)
            else:
                # Default SAPI5 speed is sometimes fast, set comfortable default
                self._engine.setProperty('rate', 175)

            # Apply configured voice_id
            if self._voice_id is not None:
                self._engine.setProperty('voice', self._voice_id)

            self._is_initialized = True
            dur = (time.perf_counter() - start_time) * 1000.0
            logger.info(f"pyttsx3 TTS engine initialized in {dur:.2f}ms.")
        except Exception as e:
            self._engine = None
            self._is_initialized = False
            raise TTSInitializationError(f"Failed to initialize pyttsx3 engine: {e}") from e

    def speak(self, text: str) -> SpeechSynthesisResult:
        """Synthesizes normalized text block and blocks until spoken."""
        if not self._is_initialized or self._engine is None:
            raise VoiceError("TextToSpeechProvider is not initialized. Call initialize() first.")

        # 1. Normalize text
        normalized_text = normalize_text_for_speech(text)
        if not normalized_text:
            return SpeechSynthesisResult(success=True, duration_seconds=0.0)

        # 2. Enforce character count bounds
        if len(normalized_text) > self._max_chars:
            logger.warning(f"TTS text exceeded limit of {self._max_chars} chars. Truncating for speech.")
            normalized_text = normalized_text[:self._max_chars] + "... [truncated]"

        logger.info(f"Speaking text (length: {len(normalized_text)} chars)")
        start_time = time.perf_counter()

        try:
            self._engine.say(normalized_text)
            self._engine.runAndWait()
            dur = time.perf_counter() - start_time
            return SpeechSynthesisResult(
                success=True,
                duration_seconds=dur,
                metadata={
                    "text_length": len(normalized_text),
                    "original_length": len(text)
                }
            )
        except Exception as e:
            logger.error(f"Error during TTS synthesis playback: {e}")
            return SpeechSynthesisResult(
                success=False,
                duration_seconds=0.0,
                metadata={"error": str(e)}
            )

    def stop(self) -> None:
        """Stops playback immediately."""
        if self._is_initialized and self._engine is not None:
            try:
                self._engine.stop()
            except Exception as e:
                logger.error(f"Error stopping pyttsx3 playback: {e}")

    def health_check(self) -> Dict[str, Any]:
        """Returns diagnostic status details."""
        rate = None
        voice = None
        if self._is_initialized and self._engine is not None:
            try:
                rate = self._engine.getProperty('rate')
                voice = self._engine.getProperty('voice')
            except Exception:
                pass
        return {
            "provider": "pyttsx3",
            "voice_id": voice or self._voice_id,
            "rate": rate or self._rate,
            "available": self._is_initialized
        }

    def shutdown(self) -> None:
        """Gracefully halts the engine reference."""
        if not self._is_initialized:
            return

        logger.info("Shutting down pyttsx3 TTS engine...")
        self.stop()
        self._engine = None
        self._is_initialized = False
        logger.info("pyttsx3 TTS engine shutdown complete.")
