"""Abstract base interface contracts for the Voice Subsystem."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from app.voice.models import AudioFrame, AudioSegment, TranscriptionResult, SpeechSynthesisResult


class AudioCapture(ABC):
    """Abstract interface for audio recording from physical or loopback input devices."""

    @abstractmethod
    def list_input_devices(self) -> List[Dict[str, Any]]:
        """Lists available audio input devices.

        Returns:
            List of device dictionaries containing id, name, is_default, and max_channels.
        """
        pass

    @abstractmethod
    def open_capture(self, device_id: Optional[int] = None) -> None:
        """Opens the audio capture stream on the specified device.

        Args:
            device_id: Optional ID of the physical device to use.
        """
        pass

    @abstractmethod
    def read_frame(self) -> AudioFrame:
        """Reads a single frame chunk of raw audio from the stream.

        Returns:
            AudioFrame: The captured frame chunk.
        """
        pass

    @abstractmethod
    def close_capture(self) -> None:
        """Closes the active audio capture stream."""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Runs diagnostics on the capture stream.

        Returns:
            Dict: Diagnostic parameters.
        """
        pass


class VoiceActivityDetector(ABC):
    """Abstract interface for voice activity detection (VAD) from streaming AudioFrames."""

    @abstractmethod
    def process_frame(self, frame: AudioFrame) -> None:
        """Processes an incoming frame of audio to update VAD state.

        Args:
            frame: The AudioFrame object to evaluate.
        """
        pass

    @abstractmethod
    def is_speech_active(self) -> bool:
        """Checks if speech is currently active."""
        pass

    @abstractmethod
    def has_speech_started(self) -> bool:
        """Checks if speech start boundary was detected in this utterance."""
        pass

    @abstractmethod
    def has_speech_ended(self) -> bool:
        """Checks if speech trailing silence boundary was detected, ending the utterance."""
        pass

    @abstractmethod
    def get_captured_segment(self) -> Optional[AudioSegment]:
        """Retrieves the full collected spoken utterance segment if complete.

        Returns:
            Optional[AudioSegment]: The finalized segment, or None if not ready.
        """
        pass

    @abstractmethod
    def reset(self) -> None:
        """Resets the VAD tracking state and buffer to receive the next utterance."""
        pass

    @abstractmethod
    def get_state(self) -> str:
        """Retrieves the current VAD state string."""
        pass


class SpeechToTextProvider(ABC):
    """Abstract interface for transcribing spoken AudioSegments to plain text."""

    @abstractmethod
    def initialize(self) -> None:
        """Initializes model resources, loading weights into memory (reused across requests)."""
        pass

    @abstractmethod
    def transcribe(self, segment: AudioSegment) -> TranscriptionResult:
        """Transcribes the given audio segment to text.

        Args:
            segment: The AudioSegment containing spoken utterance.

        Returns:
            TranscriptionResult: The transcription output.
        """
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Retrieves provider diagnostics (e.g. loaded model, execution device, computation mode)."""
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Safely shuts down the provider and releases resources."""
        pass


class TextToSpeechProvider(ABC):
    """Abstract interface for local speech synthesis from text."""

    @abstractmethod
    def initialize(self) -> None:
        """Initializes TTS engine bindings and speaker channels."""
        pass

    @abstractmethod
    def speak(self, text: str) -> SpeechSynthesisResult:
        """Synthesizes text and plays it aloud on the default speaker device.

        Args:
            text: Plain text to synthesize and speak.

        Returns:
            SpeechSynthesisResult: Synthesis metrics.
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """Interrupts and stops active speech synthesis playback instantly."""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Retrieves TTS engine state and diagnostics."""
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Releases TTS engine resources."""
        pass
