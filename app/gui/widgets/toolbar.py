"""TopToolbar widget action bar providing page title, search, and theme controls."""

from typing import Optional
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)
from PySide6.QtCore import Signal, Qt


class TopToolbar(QWidget):
    """Top action bar emitting theme_toggled signals and controlling global quick actions."""

    theme_toggled = Signal()
    about_clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("toolbarWidget")
        self.setFixedHeight(48)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)

        self.lbl_title = QLabel("Chat")
        self.lbl_title.setObjectName("headerTitle")
        layout.addWidget(self.lbl_title)

        layout.addStretch()

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search tools, commands, or documentation...")
        self.txt_search.setFixedWidth(260)
        layout.addWidget(self.txt_search)

        self.btn_theme = QPushButton("🌓 Theme")
        self.btn_theme.clicked.connect(self.theme_toggled.emit)
        layout.addWidget(self.btn_theme)

        self.btn_about = QPushButton("ⓘ About")
        self.btn_about.clicked.connect(self.about_clicked.emit)
        layout.addWidget(self.btn_about)

    def set_page_title(self, title_text: str) -> None:
        """Updates the active page title label."""
        self.lbl_title.setText(title_text)
