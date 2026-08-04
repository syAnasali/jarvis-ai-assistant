"""RegionSelectionOverlay interactive bounding box selector for screen region capture."""

from typing import Any, Optional, Tuple
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal, QPoint, QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPen


class RegionSelectionOverlay(QWidget):
    """Interactive full-screen overlay for desktop bounding box region selection."""

    region_selected = Signal(tuple)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SubWindow)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setCursor(Qt.CrossCursor)

        self._origin: Optional[QPoint] = None
        self._current: Optional[QPoint] = None
        self._selection_rect: Optional[QRect] = None


    def start_selection(self) -> None:
        """Presents full screen region selection overlay."""
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            screen_geo = app.primaryScreen().geometry()
            self.setGeometry(screen_geo)
        self.show()

    def mousePressEvent(self, event: Any) -> None:
        if event.button() == Qt.LeftButton:
            self._origin = event.pos()
            self._current = event.pos()
            self.update()

    def mouseMoveEvent(self, event: Any) -> None:
        if self._origin:
            self._current = event.pos()
            self.update()

    def mouseReleaseEvent(self, event: Any) -> None:
        if event.button() == Qt.LeftButton and self._origin and self._current:
            rect = QRect(self._origin, self._current).normalized()
            self.hide()
            bbox = (rect.x(), rect.y(), rect.width(), rect.height())
            self.region_selected.emit(bbox)
            self._origin = None
            self._current = None

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Semi-transparent dark overlay
        painter.fillRect(self.rect(), QColor(0, 0, 0, 120))

        if self._origin and self._current:
            rect = QRect(self._origin, self._current).normalized()
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(rect, Qt.transparent)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

            pen = QPen(QColor("#6366f1"), 2, Qt.DashLine)
            painter.setPen(pen)
            painter.drawRect(rect)

        painter.end()
