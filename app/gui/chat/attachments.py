"""AttachmentWidget and AttachmentBar for image, document, and clipboard file intake."""

from pathlib import Path
from typing import List, Optional
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)
from PySide6.QtCore import Signal, Qt
from app.gui.chat.models import AttachmentInfo


class AttachmentWidget(QFrame):
    """Badge representing an attached image or document file."""

    remove_requested = Signal(object)

    def __init__(self, info: AttachmentInfo, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.info = info
        self.setStyleSheet("background-color: #242838; border-radius: 4px; padding: 2px 6px;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        lbl = QLabel(f"📎 {info.filename}")
        lbl.setStyleSheet("font-size: 11px; color: #e2e8f0;")
        layout.addWidget(lbl)

        btn_del = QPushButton("×")
        btn_del.setFixedSize(16, 16)
        btn_del.setStyleSheet("border: none; color: #ef4444; font-weight: bold;")
        btn_del.clicked.connect(lambda: self.remove_requested.emit(self.info))
        layout.addWidget(btn_del)


class AttachmentBar(QWidget):
    """Horizontal intake bar holding attached file badges."""

    attachments_changed = Signal(list)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.attachments: List[AttachmentInfo] = []

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(6)
        self.layout.addStretch()

    def add_attachment(self, file_path: str) -> None:
        """Adds a file attachment by local path."""
        p = Path(file_path)
        if not p.exists():
            return

        info = AttachmentInfo(
            filename=p.name,
            file_path=str(p.resolve()),
            file_size_bytes=p.stat().st_size
        )
        self.attachments.append(info)

        badge = AttachmentWidget(info, parent=self)
        badge.remove_requested.connect(self._remove_attachment)
        self.layout.insertWidget(self.layout.count() - 1, badge)
        self.attachments_changed.emit(self.attachments)

    def _remove_attachment(self, info: AttachmentInfo) -> None:
        """Removes an attachment."""
        if info in self.attachments:
            self.attachments.remove(info)
            self.attachments_changed.emit(self.attachments)
            self.clear_ui()
            for att in self.attachments:
                badge = AttachmentWidget(att, parent=self)
                badge.remove_requested.connect(self._remove_attachment)
                self.layout.insertWidget(self.layout.count() - 1, badge)

    def clear_ui(self) -> None:
        """Clears all badges from UI."""
        while self.layout.count() > 1:
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def clear(self) -> None:
        """Clears all attachments."""
        self.attachments.clear()
        self.clear_ui()
        self.attachments_changed.emit(self.attachments)
