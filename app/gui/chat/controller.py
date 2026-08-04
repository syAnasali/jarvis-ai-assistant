"""ChatController orchestrating conversation history, QThread workers, and backend execution."""

from typing import Any, Callable, Dict, List, Optional
from PySide6.QtCore import QObject, Signal
from app.core.logger import JarvisLogger
from app.gui.chat.models import ChatMessage, ConversationSession, MessageType
from app.gui.chat.worker import ChatWorker

logger = JarvisLogger.get_logger("gui_chat_controller")


class ChatController(QObject):
    """Controller orchestrating active session messages and QThread workers."""

    message_added = Signal(ChatMessage)
    token_received = Signal(str)
    status_changed = Signal(str)
    generation_finished = Signal(str, list)
    generation_error = Signal(str)

    def __init__(self, agent_runner: Optional[Any] = None, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.agent_runner = agent_runner
        self.active_session = ConversationSession()
        self.active_worker: Optional[ChatWorker] = None

    def send_user_message(self, text: str, attachments: Optional[List[Any]] = None) -> ChatMessage:
        """Adds a user message to the session and triggers asynchronous LLM generation."""
        user_msg = ChatMessage(
            message_type=MessageType.USER,
            content=text,
            attachments=attachments or []
        )
        self.active_session.messages.append(user_msg)
        self.message_added.emit(user_msg)

        # Spawn ChatWorker off-thread
        self.active_worker = ChatWorker(
            prompt=text,
            session_id=self.active_session.session_id,
            agent_runner=self.agent_runner,
            parent=self
        )
        self.active_worker.token_received.connect(self.token_received.emit)
        self.active_worker.step_status.connect(self.status_changed.emit)
        self.active_worker.generation_completed.connect(self._on_worker_completed)
        self.active_worker.generation_failed.connect(self._on_worker_failed)
        self.active_worker.start()

        return user_msg

    def _on_worker_completed(self, full_text: str, citations: List[Dict[str, Any]]) -> None:
        """Handler for successful generation completion."""
        assistant_msg = ChatMessage(
            message_type=MessageType.ASSISTANT,
            content=full_text,
            citations=citations
        )
        self.active_session.messages.append(assistant_msg)
        self.generation_finished.emit(full_text, citations)
        self.status_changed.emit("Ready")
        self.active_worker = None

    def _on_worker_failed(self, error_msg: str) -> None:
        """Handler for generation failure."""
        err_msg = ChatMessage(
            message_type=MessageType.ERROR,
            content=f"Execution error: {error_msg}"
        )
        self.active_session.messages.append(err_msg)
        self.generation_error.emit(error_msg)
        self.status_changed.emit("Error")
        self.active_worker = None

    def cancel_generation(self) -> None:
        """Cancels active generation worker."""
        if self.active_worker and self.active_worker.isRunning():
            self.active_worker.cancel()
            self.status_changed.emit("Cancelled")

    def clear_session(self) -> None:
        """Clears active session messages."""
        self.active_session = ConversationSession()
        logger.info("Cleared active chat session.")
