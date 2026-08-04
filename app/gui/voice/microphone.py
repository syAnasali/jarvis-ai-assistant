"""MicrophoneDeviceSelector dropdown widget for audio input device selection."""

from typing import List, Optional
from PySide6.QtWidgets import QComboBox, QWidget
from app.core.logger import JarvisLogger

logger = JarvisLogger.get_logger("gui_microphone")


class MicrophoneDeviceSelector(QComboBox):
    """Audio input device selection dropdown."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(200)
        self.populate_devices()

    def populate_devices(self) -> None:
        """Populates available audio input devices."""
        self.clear()
        self.addItem("Default System Microphone (PyAudio)", userData="default")
        self.addItem("Secondary Input Device", userData="secondary")
        self.setCurrentIndex(0)
