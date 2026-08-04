"""IconManager generating vector and procedural icons for GUI controls."""

from typing import Dict, Optional
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtCore import Qt
from app.core.logger import JarvisLogger

logger = JarvisLogger.get_logger("gui_icons")


class IconManager:
    """Manages icon caching and procedural vector icon generation."""

    _icon_cache: Dict[str, QIcon] = {}

    @classmethod
    def get_icon(cls, icon_name: str, color: str = "#6366f1") -> QIcon:
        """Returns a cached or procedurally generated QIcon."""
        key = f"{icon_name}_{color}"
        if key in cls._icon_cache:
            return cls._icon_cache[key]

        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(4, 4, 16, 16)
        painter.end()

        icon = QIcon(pixmap)
        cls._icon_cache[key] = icon
        return icon
