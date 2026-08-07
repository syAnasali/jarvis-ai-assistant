"""ChatView assembling ConversationHeader, MessageListWidget, AttachmentBar, and MessageInput."""

from typing import Any, List, Optional
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import QEvent, Qt, Signal
from app.gui.chat.attachments import AttachmentBar
from app.gui.chat.controller import ChatController
from app.gui.chat.message import MessageListWidget, TypingIndicator
from app.gui.chat.models import ChatMessage, ConversationSession, MessageType
from app.gui.chat.streaming import StreamingHandler


class PastChatsDialog(QDialog):
    """Modal dialog displaying all saved past chat sessions."""

    session_selected = Signal(str)

    def __init__(self, controller: ChatController, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("📜 Past Chat History")
        self.resize(550, 400)
        self.setStyleSheet("background-color: #1a1d29; color: #f8fafc;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        lbl_title = QLabel("📜 Saved Past Chat Sessions")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #818cf8;")
        layout.addWidget(lbl_title)

        self.list_widget = QListWidget(self)
        self.list_widget.setStyleSheet(
            "QListWidget { background-color: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 4px; }"
            "QListWidget::item { padding: 8px; border-bottom: 1px solid #1e293b; color: #e2e8f0; }"
            "QListWidget::item:selected { background-color: #312e81; color: #ffffff; }"
        )
        layout.addWidget(self.list_widget)

        self._populate_list()

        btn_row = QHBoxLayout()
        btn_open = QPushButton("Open Selected Chat")
        btn_open.setStyleSheet("background-color: #4f46e5; color: #ffffff; font-weight: bold; padding: 6px 12px; border-radius: 6px;")
        btn_open.clicked.connect(self._on_open_clicked)
        btn_row.addWidget(btn_open)

        btn_del = QPushButton("Delete Selected")
        btn_del.setStyleSheet("background-color: #991b1b; color: #ffffff; padding: 6px 12px; border-radius: 6px;")
        btn_del.clicked.connect(self._on_delete_clicked)
        btn_row.addWidget(btn_del)

        btn_row.addStretch()
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)

        layout.addLayout(btn_row)

    def _populate_list(self) -> None:
        self.list_widget.clear()
        for sess in self.controller.sessions:
            msg_count = len(sess.messages)
            active_marker = " (Active)" if sess.session_id == self.controller.active_session.session_id else ""
            ts_str = sess.created_at.strftime("%Y-%m-%d %H:%M") if hasattr(sess.created_at, "strftime") else str(sess.created_at)[:19]
            item_text = f"💬 {sess.title}{active_marker}\n   ID: {sess.session_id} | {msg_count} messages | {ts_str}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, sess.session_id)
            self.list_widget.addItem(item)

    def _on_open_clicked(self) -> None:
        curr = self.list_widget.currentItem()
        if curr:
            sess_id = curr.data(Qt.UserRole)
            self.session_selected.emit(sess_id)
            self.accept()

    def _on_delete_clicked(self) -> None:
        curr = self.list_widget.currentItem()
        if curr:
            sess_id = curr.data(Qt.UserRole)
            self.controller.delete_session(sess_id)
            self._populate_list()


class ConversationHeader(QWidget):
    """Header bar with New Chat, Past Chats, Clear Chat, and Export controls."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(38)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(8)

        self.btn_new = QPushButton("➕ New Chat")
        self.btn_new.setFixedSize(90, 26)
        layout.addWidget(self.btn_new)

        self.btn_history = QPushButton("📜 Past Chats")
        self.btn_history.setFixedSize(100, 26)
        layout.addWidget(self.btn_history)

        self.btn_clear = QPushButton("🗑️ Clear Thread")
        self.btn_clear.setFixedSize(110, 26)
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
        self.header.btn_history.clicked.connect(self._open_past_chats)
        self.header.btn_clear.clicked.connect(self._on_clear_chat)
        self.message_input.btn_send.clicked.connect(self._on_send_clicked)

        self.controller.message_added.connect(self._on_message_added)
        self.controller.token_received.connect(self._on_token_received)
        self.controller.status_changed.connect(self._on_status_changed)
        self.controller.generation_finished.connect(self._on_generation_finished)
        self.controller.generation_error.connect(self._on_generation_error)
        self.controller.session_switched.connect(self._on_session_switched)

        # Render saved conversation messages
        self._load_saved_messages()

    def _load_saved_messages(self) -> None:
        """Renders saved conversation session messages on startup or session switch."""
        self.message_list.clear_messages()
        for msg in self.controller.active_session.messages:
            self.message_list.add_message(msg)

    def _open_past_chats(self) -> None:
        """Opens modal dialog listing all saved past chat sessions."""
        dialog = PastChatsDialog(self.controller, parent=self)
        dialog.session_selected.connect(self.controller.switch_session)
        dialog.exec()

    def _on_session_switched(self, session: ConversationSession) -> None:
        """Handles session switch events by reloading thread bubbles."""
        self._load_saved_messages()

    def _on_send_clicked(self) -> None:
        text = self.message_input.get_text()
        if not text:
            return

        attachments = list(self.message_input.attachment_bar.attachments)
        self.message_input.clear_text()
        self.message_input.attachment_bar.clear()

        # Send user message first so User bubble is placed above Streaming Assistant bubble
        self.controller.send_user_message(text, attachments)
        self.streaming_handler.start_streaming()

    def _on_message_added(self, msg: ChatMessage) -> None:
        if msg.message_type == MessageType.ASSISTANT:
            self.streaming_handler.finish_streaming()
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

    def _on_generation_error(self, error_msg: str) -> None:
        self.streaming_handler.finish_streaming()

    def _on_new_chat(self) -> None:
        self.controller.create_new_session()

    def _on_clear_chat(self) -> None:
        self.controller.clear_session()
        self.message_list.clear_messages()
