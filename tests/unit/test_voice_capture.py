"""Unit tests for the Audio Capture abstraction."""

import pytest
from unittest.mock import MagicMock, patch

from app.voice.capture import (
    SoundDeviceAudioCapture,
    AudioDeviceNotFoundError,
    AudioDeviceUnavailableError,
    AudioCaptureFailedError,
)


@patch("sounddevice.query_devices")
@patch("sounddevice.default")
def test_list_input_devices(mock_default, mock_query) -> None:
    # Set up mock query_devices returning input & output devices
    mock_query.return_value = [
        {"name": "Mic 1", "max_input_channels": 2, "max_output_channels": 0},
        {"name": "Speaker 1", "max_input_channels": 0, "max_output_channels": 2},
        {"name": "Mic 2", "max_input_channels": 1, "max_output_channels": 0},
    ]
    mock_default.device = [0, 1]

    capture = SoundDeviceAudioCapture()
    devices = capture.list_input_devices()

    # Should only filter for input devices (Mic 1, Mic 2)
    assert len(devices) == 2
    assert devices[0]["name"] == "Mic 1"
    assert devices[0]["device_id"] == 0
    assert devices[0]["is_default"] is True
    assert devices[1]["name"] == "Mic 2"
    assert devices[1]["device_id"] == 2
    assert devices[1]["is_default"] is False


@patch("sounddevice.query_devices")
def test_open_capture_no_devices(mock_query) -> None:
    # No devices returned
    mock_query.return_value = []
    capture = SoundDeviceAudioCapture()

    with pytest.raises(AudioDeviceNotFoundError, match="No input audio devices detected"):
        capture.open_capture()


@patch("sounddevice.query_devices")
def test_open_capture_invalid_id(mock_query) -> None:
    mock_query.return_value = [
        {"name": "Mic 1", "max_input_channels": 2, "max_output_channels": 0}
    ]
    capture = SoundDeviceAudioCapture()

    with pytest.raises(AudioDeviceNotFoundError, match="Device with ID 99 not found"):
        capture.open_capture(device_id=99)


def test_read_frame_when_not_open() -> None:
    capture = SoundDeviceAudioCapture()
    with pytest.raises(AudioCaptureFailedError, match="stream is not open"):
        capture.read_frame()
