"""ApprovalDetailsWidget inspector panel rendering action parameters and risk evaluation."""

from typing import Any, Dict, Optional
from PySide6.QtWidgets import QFrame, QLabel, QPlainTextEdit, QVBoxLayout, QWidget
from PySide6.QtCore import Qt
from app.gui.approval.risk import RiskBadgeWidget


class ApprovalDetailsWidget(QFrame):
    """Inspector panel displaying tool action arguments and security risk details."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.setStyleSheet("background-color: #1a1d29; border: 1px solid #242838; border-radius: 8px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        lbl_hdr = QLabel("🔍 Tool Action Inspector")
        lbl_hdr.setStyleSheet("font-weight: 600; color: #818cf8; font-size: 12px;")
        layout.addWidget(lbl_hdr)

        self.risk_badge = RiskBadgeWidget("CONFIRMATION", self)
        layout.addWidget(self.risk_badge)

        self.lbl_tool = QLabel("Tool: -")
        self.lbl_tool.setStyleSheet("color: #e2e8f0; font-size: 13px; font-weight: 600;")
        layout.addWidget(self.lbl_tool)

        self.lbl_source = QLabel("Source: -")
        self.lbl_source.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(self.lbl_source)

        lbl_args = QLabel("Arguments Payload:")
        lbl_args.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(lbl_args)

        self.txt_payload = QPlainTextEdit()
        self.txt_payload.setReadOnly(True)
        self.txt_payload.setStyleSheet("background-color: #12141c; color: #38bdf8; font-family: Consolas; font-size: 11px; border: none;")
        layout.addWidget(self.txt_payload)

    def set_action(self, action_dict: Dict[str, Any]) -> None:
        """Sets selected pending action details."""
        self.lbl_tool.setText(f"Tool: {action_dict.get('tool_name', 'Unknown Tool')}")
        self.lbl_source.setText(f"Source: {action_dict.get('source', 'User Request')}")
        self.risk_badge.set_risk_level(action_dict.get("risk_level", "CONFIRMATION"))
        self.txt_payload.setPlainText(str(action_dict.get("arguments", {})))
