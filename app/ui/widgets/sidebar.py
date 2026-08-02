"""Right Sidebar widget showing state, session info, and pending approvals."""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QListWidget, QListWidgetItem
from PySide6.QtCore import Qt
from app.ui.theme import TEXT_PRIMARY, TEXT_SECONDARY, BORDER_COLOR, ACCENT_BLUE, BG_CARD


class SidebarWidget(QFrame):
    """Sidebar display panel detailing database records, session info, and approvals."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedWidth(240)
        self.setObjectName("sidebar")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # Sidebar Header
        header = QLabel("METRICS & STATE")
        header.setObjectName("sidebarHeader")
        layout.addWidget(header)
        
        # State Indicators Layout
        self.session_lbl = QLabel("Session: N/A")
        self.session_lbl.setWordWrap(True)
        self.session_lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
        layout.addWidget(self.session_lbl)
        
        self.state_lbl = QLabel("State: Idle")
        self.state_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-weight: bold;")
        layout.addWidget(self.state_lbl)
        
        self.model_lbl = QLabel("Model: N/A")
        self.model_lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
        layout.addWidget(self.model_lbl)
        
        # Counts Box
        self.counts_lbl = QLabel("Memory Count: 0\nConversations: 0")
        self.counts_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; padding: 8px; background: {BG_CARD}; border: 1px solid {BORDER_COLOR}; border-radius: 4px;")
        layout.addWidget(self.counts_lbl)
        
        # Approvals Section Header
        approvals_hdr = QLabel("PENDING APPROVALS")
        approvals_hdr.setStyleSheet(f"color: {TEXT_PRIMARY}; font-weight: bold; font-size: 11px; margin-top: 10px;")
        layout.addWidget(approvals_hdr)
        
        # List of pending approvals
        self.approvals_list = QListWidget()
        self.approvals_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER_COLOR};
                border-radius: 4px;
                color: {TEXT_PRIMARY};
            }}
            QListWidget::item {{
                padding: 6px;
                border-bottom: 1px solid {BORDER_COLOR};
            }}
        """)
        layout.addWidget(self.approvals_list)
        
        layout.addStretch()

    def update_session_info(self, session_id: str) -> None:
        self.session_lbl.setText(f"Session:\n{session_id}")

    def update_state(self, state_text: str) -> None:
        self.state_lbl.setText(f"State: {state_text}")

    def update_model(self, model_name: str) -> None:
        self.model_lbl.setText(f"Model: {model_name}")

    def update_counts(self, memory_count: int, conversation_count: int) -> None:
        self.counts_lbl.setText(f"Memory Count: {memory_count}\nConversations: {conversation_count}")

    def set_pending_approvals(self, pending_actions: list) -> None:
        """Fills approvals list widget."""
        self.approvals_list.clear()
        if not pending_actions:
            item = QListWidgetItem("No pending actions")
            item.setFlags(Qt.NoItemFlags)
            item.setForeground(Qt.gray)
            self.approvals_list.addItem(item)
            return
            
        for action in pending_actions:
            item = QListWidgetItem(f"{action.tool_name}\n({action.action_id[:8]})")
            item.setToolTip(f"ID: {action.action_id}\nTool: {action.tool_name}")
            self.approvals_list.addItem(item)
