"""HealthOverviewWidget presenting health status badges for all 8 core subsystems."""

from typing import Dict, Optional
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import Qt


class HealthOverviewWidget(QFrame):
    """Health status panel displaying status badges for all 8 core subsystems."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.setStyleSheet("background-color: #181b26; border: 1px solid #242838; border-radius: 8px;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        self.status_labels: Dict[str, QLabel] = {}
        subsystems = ["Agent", "LLM", "Memory", "Knowledge", "Planner", "Voice", "Vision", "Plugins"]

        for sub in subsystems:
            card = QWidget()
            v_layout = QVBoxLayout(card)
            v_layout.setContentsMargins(0, 0, 0, 0)
            v_layout.setSpacing(2)

            lbl_title = QLabel(sub)
            lbl_title.setStyleSheet("font-size: 11px; color: #94a3b8; font-weight: 500;")
            v_layout.addWidget(lbl_title)

            lbl_val = QLabel("🟢 HEALTHY")
            lbl_val.setStyleSheet("font-size: 11px; font-weight: 700; color: #10b981;")
            v_layout.addWidget(lbl_val)

            self.status_labels[sub] = lbl_val
            layout.addWidget(card)

    def update_health(self, health_dict: Dict[str, str]) -> None:
        """Updates subsystem health badges."""
        for sub, status in health_dict.items():
            if sub in self.status_labels:
                lbl = self.status_labels[sub]
                if status.upper() == "HEALTHY":
                    lbl.setText("🟢 HEALTHY")
                    lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #10b981;")
                elif status.upper() == "DEGRADED":
                    lbl.setText("🟡 DEGRADED")
                    lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #fbbf24;")
                else:
                    lbl.setText("🔴 DOWN")
                    lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #ef4444;")
