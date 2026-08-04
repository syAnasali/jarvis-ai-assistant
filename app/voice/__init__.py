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
    WakeWordDetector,
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
from app.voice.wakeword import LocalWakeWordDetector, WakeWordMode
from app.voice.stt import FasterWhisperSTTProvider, STTInitializationError, FasterWhisperSTTProvider as FasterWhisperProvider
from app.voice.tts import PyTTSx3TTSProvider, PiperProvider, TTSInitializationError
from app.voice.session import VoiceSession
from app.voice.playback import PlaybackManager
from app.voice.pipeline import VoicePipeline
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
    "WakeWordDetector",
    "SpeechToTextProvider",
    "TextToSpeechProvider",
    "SoundDeviceAudioCapture",
    "AudioDeviceNotFoundError",
    "AudioDeviceUnavailableError",
    "AudioCaptureFailedError",
    "EnergyBasedVAD",
    "LocalWakeWordDetector",
    "WakeWordMode",
    "FasterWhisperSTTProvider",
    "FasterWhisperProvider",
    "STTInitializationError",
    "PyTTSx3TTSProvider",
    "PiperProvider",
    "TTSInitializationError",
    "VoiceSession",
    "PlaybackManager",
    "VoicePipeline",
    "VoiceManager",
    "VoiceRuntime",
]
