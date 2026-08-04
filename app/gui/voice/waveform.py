"""WaveformWidget animated microphone volume level meter for Voice Workspace."""

from typing import Any, List, Optional
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QPainter, QBrush


class WaveformWidget(QWidget):
    """Animated microphone volume level meter displaying dynamic audio bars."""

    def __init__(self, num_bars: int = 20, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(48)
        self.num_bars = num_bars
        self.bars: List[float] = [0.1] * num_bars
        self.target_level: float = 0.1

        # Smooth animation timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate_step)
        self.timer.start(30)

    def set_amplitude(self, amplitude: float) -> None:
        """Sets target audio volume level (0.0 to 1.0)."""
        self.target_level = max(0.05, min(1.0, amplitude))

    def _animate_step(self) -> None:
        """Updates bar heights towards target level for visual animation."""
        import random
        for i in range(self.num_bars):
            jitter = random.uniform(-0.15, 0.15)
            new_val = self.target_level + jitter
            self.bars[i] = self.bars[i] * 0.7 + max(0.05, min(1.0, new_val)) * 0.3
        self.update()

    def paintEvent(self, event: Any) -> None:
        """Paints animated audio bars on QPainter canvas."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)

        w = self.width()
        h = self.height()
        bar_width = max(3.0, (w - (self.num_bars * 3)) / self.num_bars)

        for i, val in enumerate(self.bars):
            bar_height = max(4.0, val * (h - 8))
            x = i * (bar_width + 3) + 4
            y = (h - bar_height) / 2.0

            color = QColor("#6366f1") if val > 0.3 else QColor("#818cf8")
            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(x, y, bar_width, bar_height, 2, 2)

        painter.end()
