"""LoadingOverlay spinner widget for long-running asynchronous operation feedback."""

from typing import Optional
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import Qt


class LoadingOverlay(QWidget):
    """Semi-transparent loading overlay displaying an animated progress spinner."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.hide()

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        self.lbl_text = QLabel("Processing request...")
        self.lbl_text.setStyleSheet("font-size: 14px; font-weight: 600; color: #6366f1;")
        layout.addWidget(self.lbl_text)

    def show_loading(self, message: str = "Processing request...") -> None:
        """Displays loading overlay with custom text."""
        self.lbl_text.setText(message)
        self.show()

    def hide_loading(self) -> None:
        """Hides loading overlay."""
        self.hide()
