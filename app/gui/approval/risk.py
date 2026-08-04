"""RiskBadgeWidget rendering color-coded security risk level badges."""

from typing import Optional
from PySide6.QtWidgets import QLabel, QWidget


class RiskBadgeWidget(QLabel):
    """Badge label rendering SAFE, CONFIRMATION, or RESTRICTED risk levels."""

    def __init__(self, risk_level: str = "CONFIRMATION", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.set_risk_level(risk_level)

    def set_risk_level(self, risk_level: str) -> None:
        """Sets risk level text and color styling."""
        level_upper = risk_level.upper()
        if level_upper == "SAFE":
            self.setText("🟢 SAFE")
            self.setStyleSheet("background-color: #065f46; color: #34d399; font-weight: 700; font-size: 11px; border-radius: 4px; padding: 2px 8px;")
        elif level_upper in ("RESTRICTED", "HIGH", "CRITICAL"):
            self.setText("🔴 RESTRICTED")
            self.setStyleSheet("background-color: #450a0a; color: #f87171; font-weight: 700; font-size: 11px; border-radius: 4px; padding: 2px 8px;")
        else:  # CONFIRMATION / MEDIUM
            self.setText("🟡 CONFIRMATION")
            self.setStyleSheet("background-color: #451a03; color: #fbbf24; font-weight: 700; font-size: 11px; border-radius: 4px; padding: 2px 8px;")
