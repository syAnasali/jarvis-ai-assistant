"""RecoveryPanelWidget displaying retry history, recovery strategy, and rollback status."""

from typing import Dict, List, Optional
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import Qt


class RecoveryPanelWidget(QFrame):
    """Recovery panel presenting node retry history and self-correction strategies."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.setStyleSheet("background-color: #1a1d29; border: 1px solid #242838; border-radius: 8px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        lbl_hdr = QLabel("🛡️ Recovery & Rollback Engine")
        lbl_hdr.setStyleSheet("font-weight: 600; color: #fbbf24; font-size: 12px;")
        layout.addWidget(lbl_hdr)

        self.lbl_strategy = QLabel("Strategy: Retry with Exponential Backoff")
        self.lbl_strategy.setStyleSheet("color: #e2e8f0; font-size: 11px;")
        layout.addWidget(self.lbl_strategy)

        self.lbl_retries = QLabel("Retries Attempted: 0 / 3")
        self.lbl_retries.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(self.lbl_retries)

        self.lbl_rollback = QLabel("Rollback Status: Clean (No state mutation rollback needed)")
        self.lbl_rollback.setStyleSheet("color: #34d399; font-size: 11px;")
        layout.addWidget(self.lbl_rollback)

    def update_recovery_info(self, strategy: str, retries: int, max_retries: int, rollback_status: str) -> None:
        """Updates recovery panel status labels."""
        self.lbl_strategy.setText(f"Strategy: {strategy}")
        self.lbl_retries.setText(f"Retries Attempted: {retries} / {max_retries}")
        self.lbl_rollback.setText(f"Rollback Status: {rollback_status}")
