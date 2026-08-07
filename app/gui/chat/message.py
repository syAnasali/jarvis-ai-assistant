"""MessageBubble, StreamingBubble, TypingIndicator, and MessageListWidget components."""

from typing import List, Optional
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt
from app.gui.chat.citations import CitationWidget
from app.gui.chat.markdown import MarkdownRenderer
from app.gui.chat.models import ChatMessage, MessageType
from app.gui.chat.syntax import CodeBlockWidget


class MessageBubble(QWidget):
    """Rich message bubble supporting User, Assistant, Tool, Planner, Approval, and Error styles."""

    def __init__(self, message: ChatMessage, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.message = message

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 4, 12, 4)

        card = QFrame()
        card.setObjectName("cardFrame")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(6)

        # Style customization based on message type
        if message.message_type == MessageType.USER:
            main_layout.addStretch()
            main_layout.addWidget(card)
            card.setStyleSheet("background-color: #312e81; border: 1px solid #4338ca; border-radius: 12px 12px 2px 12px;")
            lbl_sender = QLabel("You")
            lbl_sender.setStyleSheet("font-weight: 600; color: #a5b4fc; font-size: 11px;")
            card_layout.addWidget(lbl_sender)

        elif message.message_type == MessageType.ASSISTANT:
            main_layout.addWidget(card)
            main_layout.addStretch()
            card.setStyleSheet("background-color: #1a1d29; border: 1px solid #242838; border-radius: 12px 12px 12px 2px;")
            lbl_sender = QLabel("Jarvis")
            lbl_sender.setStyleSheet("font-weight: 600; color: #6366f1; font-size: 11px;")
            card_layout.addWidget(lbl_sender)

        elif message.message_type == MessageType.TOOL:
            main_layout.addWidget(card)
            main_layout.addStretch()
            card.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 8px;")
            tool_title = f"🛠️ Tool Execution ({message.tool_name or 'system'})"
            lbl_sender = QLabel(tool_title)
            lbl_sender.setStyleSheet("font-weight: 600; color: #38bdf8; font-size: 11px;")
            card_layout.addWidget(lbl_sender)

        elif message.message_type == MessageType.PLANNER:
            main_layout.addWidget(card)
            main_layout.addStretch()
            card.setStyleSheet("background-color: #1e1b4b; border: 1px solid #3730a3; border-radius: 8px;")
            lbl_sender = QLabel("📋 Planner Task Graph")
            lbl_sender.setStyleSheet("font-weight: 600; color: #818cf8; font-size: 11px;")
            card_layout.addWidget(lbl_sender)

        elif message.message_type == MessageType.APPROVAL:
            main_layout.addWidget(card)
            main_layout.addStretch()
            card.setStyleSheet("background-color: #451a03; border: 1px solid #78350f; border-radius: 8px;")
            lbl_sender = QLabel("⚠️ Approval Required")
            lbl_sender.setStyleSheet("font-weight: 600; color: #fbbf24; font-size: 11px;")
            card_layout.addWidget(lbl_sender)

        else:  # ERROR or SYSTEM
            main_layout.addWidget(card)
            main_layout.addStretch()
            card.setStyleSheet("background-color: #450a0a; border: 1px solid #7f1d1d; border-radius: 8px;")
            lbl_sender = QLabel("❌ Error")
            lbl_sender.setStyleSheet("font-weight: 600; color: #f87171; font-size: 11px;")
            card_layout.addWidget(lbl_sender)

        # Message Body (HTML Markdown)
        html_content = MarkdownRenderer.to_html(message.content)
        lbl_content = QLabel(html_content)
        lbl_content.setTextFormat(Qt.RichText)
        lbl_content.setWordWrap(True)
        lbl_content.setOpenExternalLinks(True)
        card_layout.addWidget(lbl_content)

        # Interactive Approval Action Bar for confirmation required messages
        if message.message_type == MessageType.APPROVAL or "requires confirmation" in message.content or "PendingAction ID:" in message.content:
            import re
            action_match = re.search(r'PendingAction ID:\s*`?([a-zA-Z0-9_\-]+)`?', message.content)
            action_id = action_match.group(1) if action_match else "action_pending"

            btn_row = QHBoxLayout()
            btn_row.setContentsMargins(0, 8, 0, 0)
            btn_row.setSpacing(10)

            btn_approve = QPushButton("✅ Approve Execution")
            btn_approve.setCursor(Qt.PointingHandCursor)
            btn_approve.setStyleSheet("""
                QPushButton {
                    background-color: #065f46;
                    color: #34d399;
                    font-weight: 700;
                    border: 1px solid #059669;
                    border-radius: 6px;
                    padding: 6px 14px;
                }
                QPushButton:hover {
                    background-color: #047857;
                    color: #ffffff;
                }
            """)

            btn_reject = QPushButton("❌ Reject")
            btn_reject.setCursor(Qt.PointingHandCursor)
            btn_reject.setStyleSheet("""
                QPushButton {
                    background-color: #7f1d1d;
                    color: #fca5a5;
                    font-weight: 600;
                    border: 1px solid #991b1b;
                    border-radius: 6px;
                    padding: 6px 14px;
                }
                QPushButton:hover {
                    background-color: #991b1b;
                    color: #ffffff;
                }
            """)

            def _on_approved():
                btn_approve.setEnabled(False)
                btn_reject.setEnabled(False)
                btn_approve.setText("✅ Approved")
                btn_approve.setStyleSheet("background-color: #047857; color: #ffffff; border-radius: 6px; padding: 6px 14px; font-weight: 700;")
                from PySide6.QtWidgets import QApplication
                app_inst = QApplication.instance()
                if app_inst:
                    for widget in app_inst.topLevelWidgets():
                        if hasattr(widget, "approval_ctrl"):
                            widget.approval_ctrl.resolve_action("APPROVED", action_id)

            def _on_rejected():
                btn_approve.setEnabled(False)
                btn_reject.setEnabled(False)
                btn_reject.setText("❌ Rejected")
                btn_reject.setStyleSheet("background-color: #991b1b; color: #ffffff; border-radius: 6px; padding: 6px 14px;")
                from PySide6.QtWidgets import QApplication
                app_inst = QApplication.instance()
                if app_inst:
                    for widget in app_inst.topLevelWidgets():
                        if hasattr(widget, "approval_ctrl"):
                            widget.approval_ctrl.resolve_action("rejected", action_id)

            btn_approve.clicked.connect(_on_approved)
            btn_reject.clicked.connect(_on_rejected)

            btn_row.addWidget(btn_approve)
            btn_row.addWidget(btn_reject)
            btn_row.addStretch()
            card_layout.addLayout(btn_row)

        # Render Attachments
        if message.attachments:
            from pathlib import Path
            from PySide6.QtGui import QPixmap
            att_row = QHBoxLayout()
            att_row.setContentsMargins(0, 4, 0, 0)
            att_row.setSpacing(6)
            for att in message.attachments:
                fname = getattr(att, "filename", str(att))
                fpath = getattr(att, "file_path", "")
                fsize = getattr(att, "file_size_bytes", 0)

                # Image thumbnail preview check
                if fpath and Path(fpath).suffix.lower() in (".png", ".jpg", ".jpeg", ".bmp", ".webp") and Path(fpath).exists():
                    img_card = QWidget()
                    img_layout = QVBoxLayout(img_card)
                    img_layout.setContentsMargins(0, 4, 0, 4)
                    lbl_img = QLabel()
                    pix = QPixmap(fpath)
                    if not pix.isNull():
                        lbl_img.setPixmap(pix.scaledToWidth(220, Qt.SmoothTransformation))
                        img_layout.addWidget(lbl_img)
                    lbl_tag = QLabel(f"🖼️ {fname}")
                    lbl_tag.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: bold;")
                    img_layout.addWidget(lbl_tag)
                    card_layout.addWidget(img_card)
                else:
                    size_str = f" ({fsize // 1024} KB)" if fsize > 1024 else (f" ({fsize} B)" if fsize > 0 else "")
                    lbl_att = QLabel(f"📎 {fname}{size_str}")
                    lbl_att.setStyleSheet("background-color: #242838; color: #38bdf8; border: 1px solid #3b82f6; border-radius: 4px; padding: 4px 8px; font-size: 11px;")
                    att_row.addWidget(lbl_att)
            if att_row.count() > 0:
                att_row.addStretch()
                card_layout.addLayout(att_row)

        # Render Citations
        if message.citations:
            for cit in message.citations:
                cit_widget = CitationWidget(cit, parent=self)
                card_layout.addWidget(cit_widget)


class StreamingBubble(QWidget):
    """Real-time streaming bubble for live tokens."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)

        self.card = QFrame()
        self.card.setObjectName("cardFrame")
        self.card.setStyleSheet("background-color: #1a1d29; border: 1px solid #6366f1; border-radius: 12px 12px 12px 2px;")

        c_layout = QVBoxLayout(self.card)
        c_layout.setContentsMargins(12, 10, 12, 10)

        lbl_sender = QLabel("Jarvis (Streaming...)")
        lbl_sender.setStyleSheet("font-weight: 600; color: #6366f1; font-size: 11px;")
        c_layout.addWidget(lbl_sender)

        self.lbl_body = QLabel("")
        self.lbl_body.setTextFormat(Qt.RichText)
        self.lbl_body.setWordWrap(True)
        c_layout.addWidget(self.lbl_body)

        layout.addWidget(self.card)
        layout.addStretch()

        self._raw_text = ""

    def append_token(self, token: str) -> None:
        """Appends streaming token and updates HTML content."""
        self._raw_text += token
        html = MarkdownRenderer.to_html(self._raw_text)
        self.lbl_body.setText(html)

    def get_text(self) -> str:
        """Returns raw accumulated text."""
        return self._raw_text


class TypingIndicator(QWidget):
    """Status badge showing current activity ('Thinking...', 'Calling Tool...', etc.)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 4, 16, 4)

        self.lbl_status = QLabel("⚡ Thinking...")
        self.lbl_status.setStyleSheet("color: #818cf8; font-weight: 500; font-size: 12px;")
        layout.addWidget(self.lbl_status)
        layout.addStretch()
        self.hide()

    def set_status(self, text: str) -> None:
        """Sets status text and displays indicator."""
        self.lbl_status.setText(f"⚡ {text}")
        self.show()

    def hide_status(self) -> None:
        """Hides indicator."""
        self.hide()


class MessageListWidget(QScrollArea):
    """Scrollable thread container holding message bubbles."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        self.container = QWidget()
        self.container.setStyleSheet("background-color: transparent;")
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(6)
        self.layout.addStretch()

        self.setWidget(self.container)

    def add_message(self, message: ChatMessage) -> MessageBubble:
        """Adds a MessageBubble to the thread."""
        bubble = MessageBubble(message, parent=self.container)
        self.layout.insertWidget(self.layout.count() - 1, bubble)
        self.scroll_to_bottom()
        return bubble

    def add_widget(self, widget: QWidget) -> None:
        """Adds a widget to the scroll thread."""
        self.layout.insertWidget(self.layout.count() - 1, widget)
        self.scroll_to_bottom()

    def scroll_to_bottom(self) -> None:
        """Scrolls thread to bottom."""
        QApplication = None
        sb = self.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())

    def clear_messages(self) -> None:
        """Clears all message bubbles."""
        while self.layout.count() > 1:
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
