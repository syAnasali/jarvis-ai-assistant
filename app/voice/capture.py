"""Sounddevice-based microphone audio capture implementation on Windows."""

import queue
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import numpy as np
import sounddevice as sd

from app.core.exceptions import VoiceError
from app.voice.interfaces import AudioCapture
from app.voice.models import AudioFrame
from app.core.logger import JarvisLogger

logger = JarvisLogger.get_logger("audio_capture")


class AudioDeviceNotFoundError(VoiceError):
    """Raised when the specified audio device cannot be found."""
    pass


class AudioDeviceUnavailableError(VoiceError):
    """Raised when the audio device is busy or cannot be opened."""
    pass


class AudioCaptureFailedError(VoiceError):
    """Raised when recording from the audio stream fails."""
    pass


class SoundDeviceAudioCapture(AudioCapture):
    """Captures microphone audio using PyAudio/PortAudio wrapper sounddevice."""

    def __init__(self, sample_rate: int = 16000, channels: int = 1, sample_width: int = 2) -> None:
        self._sample_rate = sample_rate
        self._channels = channels
        self._sample_width = sample_width  # 2 bytes for 16-bit PCM

        self._stream: Optional[sd.RawInputStream] = None
        self._queue: queue.Queue = queue.Queue()
        self._device_id: Optional[int] = None
        self._device_name: str = ""

    def list_input_devices(self) -> List[Dict[str, Any]]:
        """Lists all available input audio devices with normalized schema."""
        normalized_devices = []
        try:
            device_list = sd.query_devices()
            for idx, dev in enumerate(device_list):
                # Filter for input devices
                if dev.get("max_input_channels", 0) > 0:
                    normalized_devices.append({
                        "device_id": idx,
                        "name": dev.get("name", f"Device {idx}"),
                        "is_default": (idx == sd.default.device[0]),
                        "max_input_channels": dev.get("max_input_channels", 0)
                    })
        except Exception as e:
            logger.error(f"Failed to query sound devices: {e}")
        return normalized_devices

    def open_capture(self, device_id: Optional[int] = None) -> None:
        """Opens raw input stream using sounddevice library callback."""
        if self._stream is not None:
            logger.warning("Audio capture stream is already open.")
            return

        devices = self.list_input_devices()
        if not devices:
            raise AudioDeviceNotFoundError("AUDIO_DEVICE_NOT_FOUND: No input audio devices detected on the system.")

        # Resolve device_id
        resolved_device = None
        if device_id is not None:
            for dev in devices:
                if dev["device_id"] == device_id:
                    resolved_device = dev
                    break
            if not resolved_device:
                raise AudioDeviceNotFoundError(f"AUDIO_DEVICE_NOT_FOUND: Device with ID {device_id} not found.")
        else:
            # Fallback to default input device
            for dev in devices:
                if dev["is_default"]:
                    resolved_device = dev
                    break
            if not resolved_device and devices:
                resolved_device = devices[0]

        if not resolved_device:
            raise AudioDeviceNotFoundError("AUDIO_DEVICE_NOT_FOUND: Could not resolve a valid input device.")

        self._device_id = resolved_device["device_id"]
        self._device_name = resolved_device["name"]
        logger.info(f"Opening audio capture on device: '{self._device_name}' (ID: {self._device_id})")

        # Clear queue
        self._queue = queue.Queue()

        def audio_callback(indata: bytes, frames: int, time_info: Any, status: Any) -> None:
            """Puts raw captured bytes into the queue."""
            if status:
                logger.warning(f"Sounddevice callback status warning: {status}")
            self._queue.put(bytes(indata))

        try:
            # Open RawInputStream for direct byte capture (16-bit PCM = 'int16')
            self._stream = sd.RawInputStream(
                device=self._device_id,
                samplerate=self._sample_rate,
                channels=self._channels,
                dtype='int16',
                blocksize=512,  # ~32ms blocks
                callback=audio_callback
            )
            self._stream.start()
        except Exception as e:
            self._stream = None
            raise AudioDeviceUnavailableError(
                f"AUDIO_DEVICE_UNAVAILABLE: Failed to start stream on device {self._device_id}. Reason: {e}"
            ) from e

    def read_frame(self) -> AudioFrame:
        """Reads a single captured chunk frame block from the queue."""
        if self._stream is None:
            raise AudioCaptureFailedError("AUDIO_CAPTURE_FAILED: Audio capture stream is not open.")

        try:
            # Blocking pull with a timeout of 1.5 seconds
            pcm_bytes = self._queue.get(timeout=1.5)
            # Create AudioFrame with timezone-aware UTC timestamp
            return AudioFrame(
                pcm_data=pcm_bytes,
                sample_rate=self._sample_rate,
                channels=self._channels,
                sample_width=self._sample_width,
                timestamp=datetime.now(timezone.utc)
            )
        except queue.Empty:
            raise AudioCaptureFailedError("AUDIO_CAPTURE_FAILED: Read timeout. No audio frames received from microphone.")

    def close_capture(self) -> None:
        """Closes stream safely."""
        if self._stream is None:
            return

        logger.info("Closing audio capture stream.")
        try:
            self._stream.stop()
            self._stream.close()
        except Exception as e:
            logger.error(f"Error closing sounddevice stream: {e}")
        finally:
            self._stream = None
            self._device_id = None
            self._device_name = ""

    def health_check(self) -> Dict[str, Any]:
        """Provides status diagnostics."""
        is_active = (self._stream is not None and self._stream.active)
        return {
            "active": is_active,
            "device_id": self._device_id,
            "device_name": self._device_name,
            "sample_rate": self._sample_rate,
            "channels": self._channels,
            "sample_width": self._sample_width
        }
