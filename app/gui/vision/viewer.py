"""ImageViewerWidget displaying captured images with zoom, pan, and annotation overlays."""

from typing import Optional
from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from app.gui.vision.annotations import AnnotationLayerWidget


class ImageViewerWidget(QScrollArea):
    """Interactive image viewer canvas supporting image previews and bounding box annotations."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setStyleSheet("QScrollArea { border: 1px solid #242838; background-color: #12141c; border-radius: 8px; }")

        self.container = QWidget()
        self.container.setStyleSheet("background-color: #12141c;")
        layout = QVBoxLayout(self.container)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)

        self.lbl_image = QLabel("No Image Captured")
        self.lbl_image.setAlignment(Qt.AlignCenter)
        self.lbl_image.setStyleSheet("color: #64748b; font-size: 14px;")
        layout.addWidget(self.lbl_image)

        self.annotation_layer = AnnotationLayerWidget(self.lbl_image)

        self.setWidget(self.container)
        self._current_pixmap: Optional[QPixmap] = None

    def set_image_pixmap(self, pixmap: QPixmap) -> None:
        """Sets QPixmap image for preview."""
        self._current_pixmap = pixmap
        scaled = pixmap.scaled(self.width() - 20, self.height() - 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.lbl_image.setPixmap(scaled)
        self.annotation_layer.setGeometry(self.lbl_image.rect())

    def clear(self) -> None:
        """Clears current image."""
        self._current_pixmap = None
        self.lbl_image.setText("No Image Captured")
        self.annotation_layer.clear()
