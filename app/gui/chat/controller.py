import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from PySide6.QtCore import QObject, Signal
from app.core.logger import JarvisLogger
from app.gui.chat.models import ChatMessage, ConversationSession, MessageType
from app.gui.chat.worker import ChatWorker

logger = JarvisLogger.get_logger("gui_chat_controller")
STORAGE_FILE = Path("data") / "chat_history.json"


class ChatController(QObject):
    """Controller orchestrating multi-session chat history, persistence, and QThread workers."""

    message_added = Signal(ChatMessage)
    token_received = Signal(str)
    status_changed = Signal(str)
    generation_finished = Signal(str, list)
    generation_error = Signal(str)
    session_switched = Signal(ConversationSession)

    def __init__(self, agent_runner: Optional[Any] = None, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.agent_runner = agent_runner
        self.sessions: List[ConversationSession] = []
        self.active_session = ConversationSession()
        self.active_worker: Optional[ChatWorker] = None
        self.load_sessions()

    def send_user_message(self, text: str, attachments: Optional[List[Any]] = None) -> ChatMessage:
        """Adds a user message to the session and triggers asynchronous LLM generation."""
        # Auto-update session title based on first user prompt
        if not self.active_session.messages or self.active_session.title == "New Conversation":
            self.active_session.title = text[:30] + ("..." if len(text) > 30 else "")

        user_msg = ChatMessage(
            message_type=MessageType.USER,
            content=text,
            attachments=attachments or []
        )
        self.active_session.messages.append(user_msg)
        self.message_added.emit(user_msg)
        self.save_sessions()

        # Pass full conversation history for context retention
        history_snapshots = [msg.to_dict() for msg in self.active_session.messages]

        # Spawn ChatWorker off-thread
        self.active_worker = ChatWorker(
            prompt=text,
            session_id=self.active_session.session_id,
            history=history_snapshots,
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
        msg_type = MessageType.APPROVAL if ("requires confirmation" in full_text or "PendingAction ID:" in full_text) else MessageType.ASSISTANT
        assistant_msg = ChatMessage(
            message_type=msg_type,
            content=full_text,
            citations=citations
        )
        self.active_session.messages.append(assistant_msg)
        self.message_added.emit(assistant_msg)
        self.save_sessions()
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
        self.save_sessions()
        self.generation_error.emit(error_msg)
        self.status_changed.emit("Error")
        self.active_worker = None

    def create_new_session(self, title: str = "New Conversation") -> ConversationSession:
        """Creates and activates a new chat session."""
        new_sess = ConversationSession(title=title)
        self.sessions.insert(0, new_sess)
        self.active_session = new_sess
        self.save_sessions()
        self.session_switched.emit(self.active_session)
        logger.info(f"Created new chat session '{new_sess.session_id}'.")
        return new_sess

    def switch_session(self, session_id: str) -> Optional[ConversationSession]:
        """Switches active session to target session_id."""
        for s in self.sessions:
            if s.session_id == session_id:
                self.active_session = s
                self.save_sessions()
                self.session_switched.emit(self.active_session)
                logger.info(f"Switched to chat session '{session_id}'.")
                return s
        return None

    def delete_session(self, session_id: str) -> None:
        """Deletes a chat session by ID."""
        self.sessions = [s for s in self.sessions if s.session_id != session_id]
        if self.active_session.session_id == session_id:
            if self.sessions:
                self.active_session = self.sessions[0]
            else:
                self.active_session = ConversationSession()
                self.sessions.append(self.active_session)
            self.session_switched.emit(self.active_session)
        self.save_sessions()

    def save_sessions(self) -> None:
        """Persists all conversation sessions to disk."""
        try:
            STORAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "active_session_id": self.active_session.session_id,
                "sessions": [s.to_dict() for s in self.sessions]
            }
            with open(STORAGE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to persist multi-session chat history: {e}")

    def load_sessions(self) -> None:
        """Loads persisted multi-session chat history from disk."""
        try:
            if STORAGE_FILE.exists():
                with open(STORAGE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    raw_sessions = data.get("sessions", [])
                    active_id = data.get("active_session_id")
                    self.sessions = [ConversationSession.from_dict(s) for s in raw_sessions]

                    if active_id:
                        for s in self.sessions:
                            if s.session_id == active_id:
                                self.active_session = s
                                break

            if not self.sessions:
                new_s = ConversationSession()
                self.sessions.append(new_s)
                self.active_session = new_s

            logger.info(f"Loaded {len(self.sessions)} chat sessions from disk.")
        except Exception as e:
            logger.warning(f"Failed to load chat sessions: {e}")
            if not self.sessions:
                self.sessions = [ConversationSession()]
                self.active_session = self.sessions[0]

    def cancel_generation(self) -> None:
        """Cancels active generation worker."""
        if self.active_worker and self.active_worker.isRunning():
            self.active_worker.cancel()
            self.status_changed.emit("Cancelled")

    def clear_session(self) -> None:
        """Clears active session messages."""
        self.active_session.messages.clear()
        self.save_sessions()
        logger.info("Cleared active chat session.")
