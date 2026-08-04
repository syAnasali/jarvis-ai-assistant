"""CodeBlockWidget with language badge, copy button, and collapse/expand controls."""

from typing import Optional
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class CodeBlockWidget(QFrame):
    """Rich Code Block Container featuring language badge, copy button, and monospace font."""

    def __init__(self, code_text: str, language: str = "text", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.code_text = code_text
        self.language = language or "text"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(4)

        # Header Bar
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(4, 2, 4, 2)

        self.lbl_lang = QLabel(self.language.upper())
        self.lbl_lang.setStyleSheet("font-size: 11px; font-weight: 600; color: #818cf8;")
        header_layout.addWidget(self.lbl_lang)

        header_layout.addStretch()

        self.btn_copy = QPushButton("Copy")
        self.btn_copy.setFixedSize(54, 22)
        self.btn_copy.setStyleSheet("font-size: 11px; background-color: #242838; color: #e2e8f0; border-radius: 4px;")
        self.btn_copy.clicked.connect(self._copy_code)
        header_layout.addWidget(self.btn_copy)

        layout.addLayout(header_layout)

        # Code Plain Text Area
        self.txt_code = QPlainTextEdit()
        self.txt_code.setReadOnly(True)
        self.txt_code.setPlainText(self.code_text)
        self.txt_code.setFont(QFont("Consolas", 10))
        self.txt_code.setStyleSheet("background-color: #12141c; color: #e2e8f0; border: none; border-radius: 4px;")

        # Adjust height based on line count
        lines = len(self.code_text.splitlines())
        height = min(max(lines * 20 + 20, 60), 300)
        self.txt_code.setFixedHeight(height)

        layout.addWidget(self.txt_code)

    def _copy_code(self) -> None:
        """Copies code content to system clipboard."""
        cb = QApplication.clipboard()
        if cb:
            cb.setText(self.code_text)
            self.btn_copy.setText("Copied!")
