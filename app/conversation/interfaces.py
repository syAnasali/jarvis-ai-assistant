"""Repository interfaces for the conversation subsystem."""

from abc import ABC, abstractmethod
from typing import List
from app.conversation.models import ConversationSession
from app.agent.messages import Message


class ConversationRepository(ABC):
    """Abstract base repository defining persistent conversation session operations."""

    @abstractmethod
    def create_session(self, session: ConversationSession) -> None:
        """Persists a new conversation session.

        Args:
            session: The ConversationSession domain object.

        Raises:
            ConversationPersistenceError: If database persistence fails.
            ConversationValidationError: If session parameters are invalid.
        """
        pass

    @abstractmethod
    def get_session(self, session_id: str) -> ConversationSession | None:
        """Retrieves a conversation session by its ID.

        Args:
            session_id: Unique session ID.

        Returns:
            ConversationSession | None: The session object, or None if not found.

        Raises:
            ConversationPersistenceError: If database execution fails.
        """
        pass

    @abstractmethod
    def list_sessions(self) -> List[ConversationSession]:
        """Lists all conversation sessions ordered by updated_at DESC.

        Returns:
            List[ConversationSession]: List of sessions.

        Raises:
            ConversationPersistenceError: If database execution fails.
        """
        pass

    @abstractmethod
    def update_session(self, session: ConversationSession) -> None:
        """Updates an existing session's metadata, title, status, etc.

        Args:
            session: The updated ConversationSession.

        Raises:
            ConversationNotFoundError: If the session does not exist.
            ConversationPersistenceError: If database update fails.
        """
        pass

    @abstractmethod
    def close_session(self, session_id: str) -> None:
        """Marks a session as closed.

        Args:
            session_id: Unique session ID.

        Raises:
            ConversationNotFoundError: If the session does not exist.
            ConversationPersistenceError: If database execution fails.
        """
        pass

    @abstractmethod
    def add_message(self, session_id: str, message: Message) -> None:
        """Adds a message to a session.

        Sequence number must be allocated transactionally inside this operation.

        Args:
            session_id: Unique session ID.
            message: The Message to append.

        Raises:
            ConversationNotFoundError: If the session does not exist.
            SessionStateError: If the session is closed.
            ConversationPersistenceError: If database execution fails.
        """
        pass

    @abstractmethod
    def get_messages(self, session_id: str) -> List[Message]:
        """Retrieves all messages for a session ordered by sequence_number ASC.

        Args:
            session_id: Unique session ID.

        Returns:
            List[Message]: Ordered list of messages.

        Raises:
            ConversationPersistenceError: If database execution fails.
        """
        pass

    @abstractmethod
    def count_messages(self, session_id: str) -> int:
        """Counts the total number of messages in a session.

        Args:
            session_id: Unique session ID.

        Returns:
            int: The message count.

        Raises:
            ConversationPersistenceError: If database execution fails.
        """
        pass
