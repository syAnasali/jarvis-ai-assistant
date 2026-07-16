"""Domain models, enums, and validations for the Voice Subsystem."""

import copy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Any, Dict, Optional


class VoiceState(Enum):
    """Voice subsystem runtime states."""
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    TRANSCRIBING = "TRANSCRIBING"
    PROCESSING = "PROCESSING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    SPEAKING = "SPEAKING"
    ERROR = "ERROR"
    STOPPED = "STOPPED"


@dataclass(frozen=True)
class AudioFrame:
    """Represents a single captured buffer chunk of raw audio."""
    pcm_data: bytes
    sample_rate: int
    channels: int
    sample_width: int
    timestamp: datetime

    def __post_init__(self) -> None:
        # Validate non-empty PCM
        if not self.pcm_data:
            raise ValueError("Audio frame pcm_data cannot be empty.")
        
        # Validate sample rate
        if self.sample_rate <= 0:
            raise ValueError("Audio frame sample_rate must be positive.")

        # Validate channels
        if self.channels not in (1, 2):
            raise ValueError("Audio frame channels must be 1 (mono) or 2 (stereo).")

        # Validate sample width
        if self.sample_width not in (1, 2, 4):
            raise ValueError("Audio frame sample_width must be 1, 2, or 4.")

        # Validate timezone-aware timestamp
        if self.timestamp.tzinfo is None or self.timestamp.tzinfo.utcoffset(self.timestamp) is None:
            raise ValueError("Audio frame timestamp must be timezone-aware.")

    def __repr__(self) -> str:
        return (
            f"AudioFrame(sample_rate={self.sample_rate}, "
            f"channels={self.channels}, sample_width={self.sample_width}, "
            f"pcm_bytes={len(self.pcm_data)}, timestamp={self.timestamp})"
        )


@dataclass(frozen=True)
class AudioSegment:
    """Represents a full captured spoken utterance segment ready for transcription."""
    pcm_data: bytes
    sample_rate: int
    channels: int
    sample_width: int
    duration_seconds: float

    def __post_init__(self) -> None:
        # Validate non-empty PCM
        if not self.pcm_data:
            raise ValueError("Audio segment pcm_data cannot be empty.")

        # Validate sample rate
        if self.sample_rate <= 0:
            raise ValueError("Audio segment sample_rate must be positive.")

        # Validate channels
        if self.channels not in (1, 2):
            raise ValueError("Audio segment channels must be 1 (mono) or 2 (stereo).")

        # Validate sample width
        if self.sample_width not in (1, 2, 4):
            raise ValueError("Audio segment sample_width must be 1, 2, or 4.")

        # Validate duration
        if self.duration_seconds <= 0.0:
            raise ValueError("Audio segment duration_seconds must be positive.")

    def __repr__(self) -> str:
        return (
            f"AudioSegment(sample_rate={self.sample_rate}, "
            f"channels={self.channels}, sample_width={self.sample_width}, "
            f"pcm_bytes={len(self.pcm_data)}, duration_seconds={self.duration_seconds:.2f}s)"
        )


@dataclass(frozen=True)
class TranscriptionResult:
    """Encapsulates the transcription result from the Speech-to-Text engine."""
    text: str
    confidence: Optional[float] = None
    language: Optional[str] = None
    duration_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.duration_seconds < 0.0:
            raise ValueError("Transcription duration_seconds must be non-negative.")
        
        # Defensively copy metadata and make it read-only
        copied_metadata = copy.deepcopy(self.metadata)
        object.__setattr__(self, "metadata", MappingProxyType(copied_metadata))

    def __repr__(self) -> str:
        # Limit text display if long, do not leak full sensitive speech at INFO log easily
        truncated_text = self.text[:60] + "..." if len(self.text) > 60 else self.text
        return (
            f"TranscriptionResult(text='{truncated_text}', "
            f"confidence={self.confidence}, language={self.language}, "
            f"duration={self.duration_seconds:.2f}s)"
        )


@dataclass(frozen=True)
class SpeechSynthesisResult:
    """Encapsulates the synthesis result from the Text-to-Speech engine."""
    success: bool
    duration_seconds: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.duration_seconds is not None and self.duration_seconds < 0.0:
            raise ValueError("Speech synthesis duration_seconds must be non-negative.")

        # Defensively copy metadata and make it read-only
        copied_metadata = copy.deepcopy(self.metadata)
        object.__setattr__(self, "metadata", MappingProxyType(copied_metadata))

    def __repr__(self) -> str:
        return (
            f"SpeechSynthesisResult(success={self.success}, "
            f"duration={self.duration_seconds}s)"
        )
