"""ApprovalDialog modal popup for human-in-the-loop tool execution approval."""

from typing import Any, Dict, Optional
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt
from app.gui.approval.risk import RiskBadgeWidget


class ApprovalDialog(QDialog):
    """Modal pop-up approval dialog displaying tool parameters and risk badges."""

    def __init__(self, action_dict: Dict[str, Any], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Jarvis Tool Execution Approval Request")
        self.setMinimumWidth(450)
        self.action_dict = action_dict

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Header Row with Risk Badge
        hdr_row = QHBoxLayout()
        lbl_title = QLabel("⚠️ Human Approval Required")
        lbl_title.setStyleSheet("font-weight: 700; color: #fbbf24; font-size: 14px;")
        hdr_row.addWidget(lbl_title)
        hdr_row.addStretch()

        badge = RiskBadgeWidget(action_dict.get("risk_level", "RESTRICTED"), self)
        hdr_row.addWidget(badge)
        layout.addLayout(hdr_row)

        # Tool Description
        tool_name = action_dict.get("tool_name", "file_writer")
        lbl_desc = QLabel(f"Jarvis is requesting permission to execute tool: <b>{tool_name}</b>")
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #e2e8f0; font-size: 12px;")
        layout.addWidget(lbl_desc)

        # Payload Preview
        lbl_payload = QLabel("Requested Arguments / Parameters:")
        lbl_payload.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(lbl_payload)

        txt_payload = QPlainTextEdit()
        txt_payload.setReadOnly(True)
        txt_payload.setPlainText(str(action_dict.get("arguments", {})))
        txt_payload.setStyleSheet("background-color: #12141c; color: #38bdf8; font-family: Consolas; font-size: 11px; border: 1px solid #242838; border-radius: 6px;")
        layout.addWidget(txt_payload)

        # Buttons Row
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.btn_reject = QPushButton("Reject")
        self.btn_reject.setFixedWidth(90)
        self.btn_reject.setStyleSheet("background-color: #450a0a; color: #f87171; font-weight: 600; padding: 6px;")
        self.btn_reject.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_reject)

        self.btn_approve = QPushButton("Approve")
        self.btn_approve.setFixedWidth(100)
        self.btn_approve.setStyleSheet("background-color: #065f46; color: #34d399; font-weight: 700; padding: 6px;")
        self.btn_approve.clicked.connect(self.accept)
        btn_row.addWidget(self.btn_approve)

        layout.addLayout(btn_row)
