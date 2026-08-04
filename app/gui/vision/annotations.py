"""AnnotationLayerWidget rendering OCR bounding boxes and visual region highlights."""

from typing import Any, Dict, List, Optional
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QFont


class AnnotationLayerWidget(QWidget):
    """Renders bounding box annotations and labels over image canvas."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.annotations: List[Dict[str, Any]] = []

    def set_annotations(self, items: List[Dict[str, Any]]) -> None:
        """Sets list of bounding box annotation dicts: [{'bbox': (x,y,w,h), 'label': 'text'}]."""
        self.annotations = items
        self.update()

    def clear(self) -> None:
        """Clears all annotations."""
        self.annotations.clear()
        self.update()

    def paintEvent(self, event: Any) -> None:
        if not self.annotations:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        pen = QPen(QColor("#6366f1"), 2)
        painter.setPen(pen)
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))

        for ann in self.annotations:
            bbox = ann.get("bbox", (0, 0, 0, 0))
            label = ann.get("label", "")
            rect = QRect(bbox[0], bbox[1], bbox[2], bbox[3])

            painter.setBrush(QColor(99, 102, 241, 40))
            painter.drawRect(rect)

            if label:
                painter.setPen(QPen(QColor("#ffffff")))
                painter.drawText(rect.x() + 4, rect.y() - 4, label)
                painter.setPen(pen)

        painter.end()
