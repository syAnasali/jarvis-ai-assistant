"""ToastNotificationManager for non-blocking toast popups."""

from typing import Optional
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import QTimer, Qt


class ToastNotification(QWidget):
    """Non-blocking micro-animated toast notification popup."""

    def __init__(self, message: str, level: str = "info", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.SubWindow)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        lbl = QLabel(message)
        lbl.setStyleSheet("color: #ffffff; font-weight: 500;")
        layout.addWidget(lbl)

        bg_color = "#10b981" if level == "success" else "#ef4444" if level == "error" else "#6366f1"
        self.setStyleSheet(f"background-color: {bg_color}; border-radius: 6px;")

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.close)
        self.timer.start(3000)


class ToastNotificationManager:
    """Manager displaying non-blocking toast popups over MainWindow."""

    @classmethod
    def show_toast(cls, parent: QWidget, message: str, level: str = "info") -> None:
        """Creates and presents a non-blocking toast notification."""
        toast = ToastNotification(message, level=level, parent=parent)
        toast.move(parent.width() - 280, 20)
        toast.show()
