"""MessageBubble, StreamingBubble, TypingIndicator, and MessageListWidget components."""

from typing import List, Optional
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
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
