"""Manager layer coordinating conversation sessions and operations."""

from datetime import datetime, timezone
from typing import Dict, Any, List
from app.conversation.interfaces import ConversationRepository
from app.conversation.models import ConversationSession, SessionStatus
from app.agent.messages import Message
from app.core.exceptions import ConversationNotFoundError
from app.utils.id_generator import generate_session_id


class ConversationManager:
    """Manages active conversation session life cycles and persistence."""

    def __init__(self, repository: ConversationRepository) -> None:
        """Initializes ConversationManager.

        Args:
            repository: The ConversationRepository implementation to use.
        """
        self._repository = repository

    def create_session(self, title: str | None = None, metadata: Dict[str, Any] | None = None) -> ConversationSession:
        """Creates and persists a new conversation session.

        Args:
            title: Optional user-friendly title.
            metadata: Additional metadata dictionary.

        Returns:
            ConversationSession: The created session object.
        """
        now = datetime.now(timezone.utc)
        session = ConversationSession(
            session_id=generate_session_id(),
            created_at=now,
            updated_at=now,
            status=SessionStatus.ACTIVE,
            title=title,
            metadata=metadata or {},
        )
        self._repository.create_session(session)
        return session

    def load_session(self, session_id: str) -> ConversationSession:
        """Loads a session from repository by ID.

        Args:
            session_id: Unique session ID.

        Returns:
            ConversationSession: Loaded session object.

        Raises:
            ConversationNotFoundError: If the session does not exist.
        """
        session = self._repository.get_session(session_id)
        if not session:
            raise ConversationNotFoundError(f"Conversation session {session_id} not found.")
        return session

    def list_sessions(self) -> List[ConversationSession]:
        """Lists all conversation sessions ordered by updated_at DESC."""
        return self._repository.list_sessions()

    def close_session(self, session_id: str) -> None:
        """Closes a conversation session by its ID."""
        self._repository.close_session(session_id)

    def add_message(self, session_id: str, message: Message) -> None:
        """Appends a new message to the persistent session history."""
        self._repository.add_message(session_id, message)

    def get_messages(self, session_id: str) -> List[Message]:
        """Retrieves all messages for a session ordered by sequence_number ASC."""
        return self._repository.get_messages(session_id)

    def count_messages(self, session_id: str) -> int:
        """Counts the total number of messages in a session."""
        return self._repository.count_messages(session_id)
