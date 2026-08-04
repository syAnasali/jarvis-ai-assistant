from typing import Optional
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt


class ConfirmationDialog(QDialog):
    """Modal dialog prompting user for action approval."""

    def __init__(self, title: str, message: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)


class ErrorDialog(QDialog):
    """Modal dialog presenting an error traceback or message."""

    def __init__(self, title: str, error_message: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        msg_label = QLabel(error_message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("color: #ef4444; font-weight: 500;")
        layout.addWidget(msg_label)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok)
        btn_box.accepted.connect(self.accept)
        layout.addWidget(btn_box)


class AboutDialog(QDialog):
    """Modal dialog presenting application information."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("About Jarvis AI Assistant")
        self.setFixedSize(360, 200)

        layout = QVBoxLayout(self)
        title = QLabel("Jarvis AI Assistant")
        title.setObjectName("headerTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        info = QLabel("Production-Grade Autonomous Personal Assistant\nVersion 1.0.0 (Build 2026)")
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok)
        btn_box.accepted.connect(self.accept)
        layout.addWidget(btn_box)
