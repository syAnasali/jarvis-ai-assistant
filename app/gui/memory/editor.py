"""MemoryEditorWidget modal dialog for creating and editing memory records."""

from typing import Optional
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)


class MemoryEditorWidget(QDialog):
    """Modal dialog for editing or creating memory records."""

    def __init__(self, content: str = "", memory_type: str = "Fact", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Memory Record Editor")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        lbl = QLabel("Memory Content:")
        layout.addWidget(lbl)

        self.txt_content = QPlainTextEdit()
        self.txt_content.setPlainText(content)
        layout.addWidget(self.txt_content)

        lbl_t = QLabel("Memory Type:")
        layout.addWidget(lbl_t)

        self.cmb_type = QComboBox()
        self.cmb_type.addItems(["Fact", "Preference", "Project", "Context"])
        self.cmb_type.setCurrentText(memory_type)
        layout.addWidget(self.cmb_type)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def get_data(self) -> tuple[str, str]:
        """Returns tuple of (content, memory_type)."""
        return self.txt_content.toPlainText().strip(), self.cmb_type.currentText()
