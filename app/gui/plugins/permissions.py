"""PluginPermissionsWidget displaying declared permissions and security risk badges."""

from typing import List, Optional
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import Qt


class PluginPermissionsWidget(QFrame):
    """Permission viewer displaying declared plugin permissions and color-coded risk tags."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.setStyleSheet("background-color: #1a1d29; border: 1px solid #242838; border-radius: 8px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        lbl_hdr = QLabel("🛡️ Declared Security Permissions")
        lbl_hdr.setStyleSheet("font-weight: 600; color: #fbbf24; font-size: 12px;")
        layout.addWidget(lbl_hdr)

        self.tags_layout = QHBoxLayout()
        self.tags_layout.setContentsMargins(0, 0, 0, 0)
        self.tags_layout.setSpacing(6)
        self.tags_layout.addStretch()

        layout.addLayout(self.tags_layout)

    def set_permissions(self, perms: List[str]) -> None:
        """Populates permission badges."""
        self.clear()
        for p in perms:
            lbl = QLabel(f"🔒 {p}")

            if p.lower() in ("filesystem", "network"):
                lbl.setStyleSheet("background-color: #450a0a; color: #f87171; border-radius: 4px; padding: 2px 6px; font-size: 11px; font-weight: 600;")
            elif p.lower() in ("vision", "voice"):
                lbl.setStyleSheet("background-color: #312e81; color: #818cf8; border-radius: 4px; padding: 2px 6px; font-size: 11px; font-weight: 600;")
            else:
                lbl.setStyleSheet("background-color: #065f46; color: #34d399; border-radius: 4px; padding: 2px 6px; font-size: 11px; font-weight: 600;")

            self.tags_layout.insertWidget(self.tags_layout.count() - 1, lbl)

    def clear(self) -> None:
        """Clears badges."""
        while self.tags_layout.count() > 1:
            item = self.tags_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
