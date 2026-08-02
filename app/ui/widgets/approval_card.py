"""Approval card widget displaying details of pending actions with a countdown timer."""

import json
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import QTimer, Signal, Slot, Qt
from app.ui.theme import BORDER_COLOR, BG_CARD, ACCENT_GREEN, ACCENT_AMBER, ACCENT_RED, TEXT_PRIMARY, TEXT_SECONDARY


class ApprovalCardWidget(QFrame):
    """Component card for reviewing and approving/rejecting a pending action."""

    # Emitted when user clicks Approve or Reject, or when countdown expires
    # Signals: action_id (str), approved (bool)
    approval_resolved = Signal(str, bool)

    def __init__(self, action_id: str, tool_name: str, reason: str, arguments: dict, timeout_seconds: int = 30, parent=None) -> None:
        super().__init__(parent)
        self.action_id = action_id
        self.tool_name = tool_name
        self.arguments = arguments
        self.time_left = timeout_seconds
        
        self.setObjectName("approvalCard")
        self.setStyleSheet(f"""
            QFrame#approvalCard {{
                background-color: #202026;
                border: 2px solid {ACCENT_AMBER};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Header: Tool Name + Risk Level
        header_layout = QHBoxLayout()
        
        tool_label = QLabel(f"⚠️ Action Required: {tool_name}")
        tool_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #ffffff;")
        header_layout.addWidget(tool_label)
        
        header_layout.addStretch()
        
        # Determine risk level
        risk_text, risk_color = self._determine_risk(tool_name)
        risk_badge = QLabel(risk_text)
        risk_badge.setStyleSheet(f"""
            background-color: {risk_color};
            color: white;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: bold;
        """)
        header_layout.addWidget(risk_badge)
        layout.addLayout(header_layout)
        
        # Reason details
        reason_label = QLabel(f"Reason: {reason if reason else 'Execution of restricted action.'}")
        reason_label.setWordWrap(True)
        reason_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-style: italic;")
        layout.addWidget(reason_label)
        
        # Target determination
        target_val = self._extract_target(tool_name, arguments)
        target_label = QLabel(f"Target: {target_val}")
        target_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-weight: bold;")
        layout.addWidget(target_label)
        
        # Arguments details formatted nicely
        args_str = json.dumps(arguments, indent=2)
        args_label = QLabel(f"Arguments:\n{args_str}")
        args_label.setStyleSheet("font-family: 'Consolas', monospace; font-size: 11px; background: #16161a; padding: 6px; border-radius: 4px;")
        layout.addWidget(args_label)
        
        # Action Buttons Layout (Approve, Reject, Timer)
        actions_layout = QHBoxLayout()
        
        # Countdown timer label
        self.timer_label = QLabel(f"Auto-reject in {self.time_left}s")
        self.timer_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        actions_layout.addWidget(self.timer_label)
        
        actions_layout.addStretch()
        
        self.reject_btn = QPushButton("Reject")
        self.reject_btn.setCursor(Qt.PointingHandCursor)
        self.reject_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #2d181e;
                border: 1px solid {ACCENT_RED};
                color: {ACCENT_RED};
                font-weight: bold;
                padding: 6px 16px;
            }}
            QPushButton:hover {{
                background-color: {ACCENT_RED};
                color: white;
            }}
        """)
        self.reject_btn.clicked.connect(self._on_reject)
        actions_layout.addWidget(self.reject_btn)
        
        self.approve_btn = QPushButton("Approve")
        self.approve_btn.setCursor(Qt.PointingHandCursor)
        self.approve_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #162d22;
                border: 1px solid {ACCENT_GREEN};
                color: {ACCENT_GREEN};
                font-weight: bold;
                padding: 6px 16px;
            }}
            QPushButton:hover {{
                background-color: {ACCENT_GREEN};
                color: white;
            }}
        """)
        self.approve_btn.clicked.connect(self._on_approve)
        actions_layout.addWidget(self.approve_btn)
        
        layout.addLayout(actions_layout)
        
        # Set up countdown QTimer
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._on_timeout_tick)
        self.timer.start()

    def _determine_risk(self, tool_name: str) -> tuple[str, str]:
        """Classifies risk level based on tool name prefixes."""
        high_risk_keywords = ("delete", "write", "move", "launch", "type", "click", "press")
        name_lower = tool_name.lower()
        
        if any(keyword in name_lower for keyword in high_risk_keywords):
            if "delete" in name_lower:
                return "HIGH RISK", ACCENT_RED
            return "MEDIUM RISK", ACCENT_AMBER
        return "LOW RISK", ACCENT_GREEN

    def _extract_target(self, tool_name: str, arguments: dict) -> str:
        """Determines the semantic target parameter (e.g. filename, coordinate)."""
        if "path" in arguments:
            return str(arguments["path"])
        elif "text" in arguments:
            return f"Type '{arguments['text']}'"
        elif "x" in arguments and "y" in arguments:
            return f"Coordinate ({arguments['x']}, {arguments['y']})"
        elif "hwnd" in arguments:
            return f"Window HWND {arguments['hwnd']}"
        elif "key" in arguments:
            return f"Key '{arguments['key']}'"
        elif "command" in arguments:
            return str(arguments["command"])
        return "System state modification"

    @Slot()
    def _on_timeout_tick(self) -> None:
        self.time_left -= 1
        if self.time_left <= 0:
            self.timer.stop()
            self.timer_label.setText("Timed out")
            # Disable buttons to prevent race conditions
            self.approve_btn.setEnabled(False)
            self.reject_btn.setEnabled(False)
            self.approval_resolved.emit(self.action_id, False)  # Auto-reject
        else:
            self.timer_label.setText(f"Auto-reject in {self.time_left}s")

    @Slot()
    def _on_approve(self) -> None:
        self.timer.stop()
        self.approve_btn.setEnabled(False)
        self.reject_btn.setEnabled(False)
        self.approval_resolved.emit(self.action_id, True)

    @Slot()
    def _on_reject(self) -> None:
        self.timer.stop()
        self.approve_btn.setEnabled(False)
        self.reject_btn.setEnabled(False)
        self.approval_resolved.emit(self.action_id, False)
