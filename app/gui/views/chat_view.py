"""ChatView assembling ConversationHeader, MessageListWidget, AttachmentBar, and MessageInput."""

from typing import Any, List, Optional
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import QEvent, Qt
from app.gui.chat.attachments import AttachmentBar
from app.gui.chat.controller import ChatController
from app.gui.chat.message import MessageListWidget, TypingIndicator
from app.gui.chat.models import ChatMessage, MessageType
from app.gui.chat.streaming import StreamingHandler


class ConversationHeader(QWidget):
    """Header bar with New Chat, Clear Chat, Export, Copy, and Search controls."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(38)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(8)

        self.btn_new = QPushButton("➕ New Chat")
        self.btn_new.setFixedSize(90, 26)
        layout.addWidget(self.btn_new)

        self.btn_clear = QPushButton("🗑️ Clear")
        self.btn_clear.setFixedSize(70, 26)
        layout.addWidget(self.btn_clear)

        layout.addStretch()

        self.btn_export = QPushButton("📥 Export")
        self.btn_export.setFixedSize(80, 26)
        layout.addWidget(self.btn_export)


class MessageInput(QWidget):
    """Multi-line input box supporting Enter to send, Shift+Enter for newline, and character counter."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 12)
        layout.setSpacing(4)

        # Attachment Bar
        self.attachment_bar = AttachmentBar(self)
        layout.addWidget(self.attachment_bar)

        # Input Row Frame
        input_frame = QFrame()
        input_frame.setObjectName("cardFrame")
        input_frame.setStyleSheet("background-color: #1a1d29; border: 1px solid #242838; border-radius: 8px;")
        i_layout = QHBoxLayout(input_frame)
        i_layout.setContentsMargins(8, 6, 8, 6)
        i_layout.setSpacing(6)

        self.btn_attach = QPushButton("📎")
        self.btn_attach.setFixedSize(28, 28)
        self.btn_attach.setToolTip("Attach image or document")
        self.btn_attach.clicked.connect(self._browse_file)
        i_layout.addWidget(self.btn_attach)

        self.btn_voice = QPushButton("🎙️")
        self.btn_voice.setFixedSize(28, 28)
        self.btn_voice.setToolTip("Voice input (Placeholder)")
        i_layout.addWidget(self.btn_voice)

        self.txt_input = QTextEdit()
        self.txt_input.setPlaceholderText("Ask Jarvis anything... (Enter to send, Shift+Enter for newline)")
        self.txt_input.setFixedHeight(50)
        self.txt_input.installEventFilter(self)
        i_layout.addWidget(self.txt_input)

        self.btn_send = QPushButton("Send")
        self.btn_send.setFixedSize(60, 32)
        self.btn_send.setStyleSheet("background-color: #6366f1; color: #ffffff; font-weight: 600; border-radius: 6px;")
        i_layout.addWidget(self.btn_send)

        layout.addWidget(input_frame)

        # Counter row
        counter_layout = QHBoxLayout()
        counter_layout.setContentsMargins(4, 0, 4, 0)
        self.lbl_counter = QLabel("0 / 4000")
        self.lbl_counter.setStyleSheet("color: #64748b; font-size: 11px;")
        counter_layout.addStretch()
        counter_layout.addWidget(self.lbl_counter)
        layout.addLayout(counter_layout)

        self.txt_input.textChanged.connect(self._update_counter)

    def _update_counter(self) -> None:
        count = len(self.txt_input.toPlainText())
        self.lbl_counter.setText(f"{count} / 4000")

    def _browse_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Attach File", "", "All Files (*)")
        if file_path:
            self.attachment_bar.add_attachment(file_path)

    def eventFilter(self, obj: Any, event: QEvent) -> bool:
        if obj is self.txt_input and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return and not (event.modifiers() & Qt.ShiftModifier):
                self.btn_send.click()
                return True
        return super().eventFilter(obj, event)

    def get_text(self) -> str:
        return self.txt_input.toPlainText().strip()

    def clear_text(self) -> None:
        self.txt_input.clear()


class ChatView(QWidget):
    """Full-featured Chat View interface powering the PySide6 Desktop GUI."""

    def __init__(self, agent_runner: Optional[Any] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.controller = ChatController(agent_runner=agent_runner, parent=self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        self.header = ConversationHeader(self)
        layout.addWidget(self.header)

        # Scrollable Message Thread
        self.message_list = MessageListWidget(self)
        layout.addWidget(self.message_list)

        # Status Badge Indicator
        self.typing_indicator = TypingIndicator(self)
        layout.addWidget(self.typing_indicator)

        # Message Input & Attachment Bar
        self.message_input = MessageInput(self)
        layout.addWidget(self.message_input)

        # Streaming Handler
        self.streaming_handler = StreamingHandler(self.message_list)

        # Wire Signals
        self.header.btn_new.clicked.connect(self._on_new_chat)
        self.header.btn_clear.clicked.connect(self._on_clear_chat)
        self.message_input.btn_send.clicked.connect(self._on_send_clicked)

        self.controller.message_added.connect(self._on_message_added)
        self.controller.token_received.connect(self._on_token_received)
        self.controller.status_changed.connect(self._on_status_changed)
        self.controller.generation_finished.connect(self._on_generation_finished)
        self.controller.generation_error.connect(self._on_generation_error)

    def _on_send_clicked(self) -> None:
        text = self.message_input.get_text()
        if not text:
            return

        attachments = list(self.message_input.attachment_bar.attachments)
        self.message_input.clear_text()
        self.message_input.attachment_bar.clear()

        # Start streaming bubble
        self.streaming_handler.start_streaming()
        self.controller.send_user_message(text, attachments)

    def _on_message_added(self, msg: ChatMessage) -> None:
        if msg.message_type == MessageType.USER:
            self.message_list.add_message(msg)

    def _on_token_received(self, token: str) -> None:
        self.streaming_handler.on_token(token)

    def _on_status_changed(self, status: str) -> None:
        if status in ("Ready", "Cancelled", "Error"):
            self.typing_indicator.hide_status()
        else:
            self.typing_indicator.set_status(status)

    def _on_generation_finished(self, full_text: str, citations: List[Any]) -> None:
        self.streaming_handler.finish_streaming()
        msg = ChatMessage(
            message_type=MessageType.ASSISTANT,
            content=full_text,
            citations=citations
        )
        self.message_list.add_message(msg)

    def _on_generation_error(self, error_msg: str) -> None:
        self.streaming_handler.finish_streaming()
        msg = ChatMessage(
            message_type=MessageType.ERROR,
            content=f"Execution error: {error_msg}"
        )
        self.message_list.add_message(msg)

    def _on_new_chat(self) -> None:
        self.controller.clear_session()
        self.message_list.clear_messages()

    def _on_clear_chat(self) -> None:
        self.controller.clear_session()
        self.message_list.clear_messages()
