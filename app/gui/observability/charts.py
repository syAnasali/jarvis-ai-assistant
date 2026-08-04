"""TelemetryChartsWidget rendering animated live trend charts using QPainter canvas."""

from typing import Any, List, Optional
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QPolygonF
from PySide6.QtCore import QPointF


class TelemetryChartsWidget(QFrame):
    """Animated live telemetry charts presenting latency and token throughput curves."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.setMinimumHeight(180)
        self.setStyleSheet("background-color: #12141c; border: 1px solid #242838; border-radius: 8px;")

        self.latency_points: List[float] = [120.0, 140.0, 115.0, 130.0, 125.0, 150.0, 110.0, 124.0]
        self.throughput_points: List[float] = [35.0, 42.0, 38.0, 45.0, 40.0, 48.0, 42.0, 43.0]

        # Timer for live chart animation
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate_step)
        self.timer.start(500)

    def _animate_step(self) -> None:
        import random
        new_lat = max(50.0, min(300.0, self.latency_points[-1] + random.uniform(-15.0, 15.0)))
        new_tp = max(10.0, min(100.0, self.throughput_points[-1] + random.uniform(-5.0, 5.0)))

        self.latency_points.append(new_lat)
        self.throughput_points.append(new_tp)

        if len(self.latency_points) > 30:
            self.latency_points.pop(0)
            self.throughput_points.pop(0)

        self.update()

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # Title
        painter.setPen(QColor("#818cf8"))
        painter.drawText(12, 20, "📈 Real-Time Request Latency (ms) & Token Throughput (t/s)")

        # Draw Latency Trend Curve (Indigo)
        step_x = (w - 30) / max(1, len(self.latency_points) - 1)
        pen_lat = QPen(QColor("#6366f1"), 2)
        painter.setPen(pen_lat)

        points: List[QPointF] = []
        for i, val in enumerate(self.latency_points):
            x = 15 + i * step_x
            y = h - 20 - ((val / 300.0) * (h - 50))
            points.append(QPointF(x, y))

        for i in range(len(points) - 1):
            painter.drawLine(points[i], points[i + 1])

        # Draw Throughput Trend Curve (Emerald Green)
        pen_tp = QPen(QColor("#10b981"), 2, Qt.DashLine)
        painter.setPen(pen_tp)

        tp_points: List[QPointF] = []
        for i, val in enumerate(self.throughput_points):
            x = 15 + i * step_x
            y = h - 20 - ((val / 100.0) * (h - 50))
            tp_points.append(QPointF(x, y))

        for i in range(len(tp_points) - 1):
            painter.drawLine(tp_points[i], tp_points[i + 1])

        painter.end()
