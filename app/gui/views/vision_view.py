"""VisionView assembling Screen Capture toolbar, ImageViewerWidget, OCR panel, and Visual Reasoning panel."""

from typing import Any, Optional
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from app.gui.vision.controller import VisionController
from app.gui.vision.overlays import RegionSelectionOverlay
from app.gui.vision.viewer import ImageViewerWidget


class VisionView(QWidget):
    """Vision Workspace interface powering screen capture, region selection, and OCR inspection."""

    def __init__(self, vision_pipeline: Optional[Any] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.controller = VisionController(vision_pipeline=vision_pipeline, parent=self)
        self.region_overlay = RegionSelectionOverlay(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. Header & Capture Toolbar
        hdr_layout = QHBoxLayout()
        lbl_title = QLabel("Local Vision Runtime Workspace")
        lbl_title.setObjectName("headerTitle")
        hdr_layout.addWidget(lbl_title)
        hdr_layout.addStretch()

        self.btn_full = QPushButton("🖥️ Full Screen")
        self.btn_full.clicked.connect(lambda: self.controller.capture_screen("full_screen"))
        hdr_layout.addWidget(self.btn_full)

        self.btn_window = QPushButton("🪟 Active Window")
        self.btn_window.clicked.connect(lambda: self.controller.capture_screen("active_window"))
        hdr_layout.addWidget(self.btn_window)

        self.btn_region = QPushButton("📐 Capture Region")
        self.btn_region.clicked.connect(self.region_overlay.start_selection)
        hdr_layout.addWidget(self.btn_region)

        self.btn_clipboard = QPushButton("📋 Clipboard Image")
        self.btn_clipboard.clicked.connect(lambda: self.controller.capture_screen("clipboard"))
        hdr_layout.addWidget(self.btn_clipboard)

        layout.addLayout(hdr_layout)

        # 2. Main Content Splitter (Left: ImageViewerWidget | Right: OCR & Reasoning Panels)
        splitter = QSplitter(Qt.Horizontal)

        # Left: Image Viewer
        self.image_viewer = ImageViewerWidget(self)
        splitter.addWidget(self.image_viewer)

        # Right: OCR + Visual Reasoning Frame
        right_panel = QWidget()
        r_layout = QVBoxLayout(right_panel)
        r_layout.setContentsMargins(0, 0, 0, 0)
        r_layout.setSpacing(8)

        # OCR Panel
        ocr_frame = QFrame()
        ocr_frame.setObjectName("cardFrame")
        o_layout = QVBoxLayout(ocr_frame)
        o_layout.setContentsMargins(8, 8, 8, 8)

        lbl_ocr = QLabel("🔤 Extracted OCR Text Panel:")
        lbl_ocr.setStyleSheet("font-weight: 600; color: #818cf8; font-size: 11px;")
        o_layout.addWidget(lbl_ocr)

        self.txt_ocr = QPlainTextEdit()
        self.txt_ocr.setReadOnly(True)
        self.txt_ocr.setPlaceholderText("OCR text results will appear here...")
        self.txt_ocr.setStyleSheet("background-color: #12141c; color: #e2e8f0; border: none;")
        o_layout.addWidget(self.txt_ocr)

        r_layout.addWidget(ocr_frame)

        # Visual Reasoning Panel
        reason_frame = QFrame()
        reason_frame.setObjectName("cardFrame")
        res_layout = QVBoxLayout(reason_frame)
        res_layout.setContentsMargins(8, 8, 8, 8)

        lbl_reason = QLabel("👁️ Visual Reasoning Output:")
        lbl_reason.setStyleSheet("font-weight: 600; color: #6366f1; font-size: 11px;")
        res_layout.addWidget(lbl_reason)

        self.txt_reasoning = QPlainTextEdit()
        self.txt_reasoning.setReadOnly(True)
        self.txt_reasoning.setPlaceholderText("Visual reasoning output will appear here...")
        self.txt_reasoning.setStyleSheet("background-color: #12141c; color: #e2e8f0; border: none;")
        res_layout.addWidget(self.txt_reasoning)

        r_layout.addWidget(reason_frame)
        splitter.addWidget(right_panel)

        splitter.setSizes([500, 400])
        layout.addWidget(splitter)

        # Wire Signals
        self.region_overlay.region_selected.connect(lambda bbox: self.controller.capture_screen("region", bbox))
        self.controller.image_captured.connect(self._on_image_captured)
        self.controller.ocr_extracted.connect(self._on_ocr_extracted)
        self.controller.reasoning_finished.connect(self._on_reasoning_finished)

    def _on_image_captured(self, pixmap: QPixmap, path: str) -> None:
        self.image_viewer.set_image_pixmap(pixmap)

    def _on_ocr_extracted(self, ocr_text: str, annotations: list) -> None:
        self.txt_ocr.setPlainText(ocr_text)
        self.image_viewer.annotation_layer.set_annotations(annotations)

    def _on_reasoning_finished(self, reasoning_text: str) -> None:
        self.txt_reasoning.setPlainText(reasoning_text)
