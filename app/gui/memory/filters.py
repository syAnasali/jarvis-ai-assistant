"""MemoryFilterWidget dropdown filters for memory type and importance."""

from typing import Optional
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QWidget


class MemoryFilterWidget(QWidget):
    """Filter bar for memory type and importance selection."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        lbl_type = QLabel("Type:")
        lbl_type.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(lbl_type)

        self.cmb_type = QComboBox()
        self.cmb_type.addItems(["All Types", "Fact", "Preference", "Project", "Context"])
        layout.addWidget(self.cmb_type)

        lbl_imp = QLabel("Importance:")
        lbl_imp.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(lbl_imp)

        self.cmb_importance = QComboBox()
        self.cmb_importance.addItems(["All Levels", "High", "Medium", "Low"])
        layout.addWidget(self.cmb_importance)
