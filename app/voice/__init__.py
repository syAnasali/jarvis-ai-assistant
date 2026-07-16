"""Voice Subsystem package exports."""

from app.voice.models import (
    VoiceState,
    AudioFrame,
    AudioSegment,
    TranscriptionResult,
    SpeechSynthesisResult,
)
from app.voice.interfaces import (
    AudioCapture,
    VoiceActivityDetector,
    SpeechToTextProvider,
    TextToSpeechProvider,
)
from app.voice.capture import (
    SoundDeviceAudioCapture,
    AudioDeviceNotFoundError,
    AudioDeviceUnavailableError,
    AudioCaptureFailedError,
)
from app.voice.vad import EnergyBasedVAD
from app.voice.stt import FasterWhisperSTTProvider, STTInitializationError
from app.voice.tts import PyTTSx3TTSProvider, TTSInitializationError
from app.voice.manager import VoiceManager
from app.voice.runtime import VoiceRuntime

__all__ = [
    "VoiceState",
    "AudioFrame",
    "AudioSegment",
    "TranscriptionResult",
    "SpeechSynthesisResult",
    "AudioCapture",
    "VoiceActivityDetector",
    "SpeechToTextProvider",
    "TextToSpeechProvider",
    "SoundDeviceAudioCapture",
    "AudioDeviceNotFoundError",
    "AudioDeviceUnavailableError",
    "AudioCaptureFailedError",
    "EnergyBasedVAD",
    "FasterWhisperSTTProvider",
    "STTInitializationError",
    "PyTTSx3TTSProvider",
    "TTSInitializationError",
    "VoiceManager",
    "VoiceRuntime",
]
