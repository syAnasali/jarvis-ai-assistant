"""SQLite-backed conversation repository implementation."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, List
from app.config.settings import settings
from app.core.exceptions import (
    ConversationError,
    ConversationValidationError,
    ConversationNotFoundError,
    ConversationPersistenceError,
    SessionStateError,
)
from app.conversation.interfaces import ConversationRepository
from app.conversation.models import ConversationSession, SessionStatus
from app.agent.messages import Message, MessageRole


class SQLiteConversationRepository(ConversationRepository):
    """SQLite implementation of the ConversationRepository interface."""

    def __init__(self, database_path: Path | None = None) -> None:
        """Initializes the repository and establishes database schema.

        Args:
            database_path: Optional path override for database.
        """
        self._db_path = database_path or settings.database_path
        self._init_db()

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Provides a thread-safe connection context manager."""
        conn = None
        try:
            # Ensure database directory exists
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(self._db_path))
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
        except sqlite3.Error as e:
            raise ConversationPersistenceError(f"Failed to connect to database: {e}") from e

        try:
            yield conn
        finally:
            if conn:
                conn.close()

    def _init_db(self) -> None:
        """Creates the conversation tables and indexes if they do not already exist."""
        try:
            with self._connection() as conn:
                with conn:
                    # Create sessions table
                    conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS conversation_sessions (
                            session_id TEXT PRIMARY KEY,
                            created_at TEXT NOT NULL,
                            updated_at TEXT NOT NULL,
                            status TEXT NOT NULL,
                            title TEXT,
                            metadata TEXT NOT NULL
                        )
                        """
                    )
                    # Create messages table
                    conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS conversation_messages (
                            message_id TEXT PRIMARY KEY,
                            session_id TEXT NOT NULL,
                            role TEXT NOT NULL,
                            content TEXT NOT NULL,
                            timestamp TEXT NOT NULL,
                            metadata TEXT NOT NULL,
                            sequence_number INTEGER NOT NULL,
                            FOREIGN KEY(session_id) REFERENCES conversation_sessions(session_id),
                            UNIQUE(session_id, sequence_number)
                        )
                        """
                    )
                    # Create indexes
                    conn.execute(
                        "CREATE INDEX IF NOT EXISTS idx_msg_session_seq ON conversation_messages(session_id, sequence_number);"
                    )
                    conn.execute(
                        "CREATE INDEX IF NOT EXISTS idx_sess_updated ON conversation_sessions(updated_at);"
                    )
        except sqlite3.Error as e:
            raise ConversationPersistenceError(f"Failed to initialize database schema: {e}") from e

    def create_session(self, session: ConversationSession) -> None:
        """Persists a new conversation session."""
        if session.created_at.tzinfo is None or session.updated_at.tzinfo is None:
            raise ConversationValidationError("Datetime objects must be timezone-aware.")

        try:
            metadata_str = json.dumps(session.metadata)
        except (TypeError, ValueError) as e:
            raise ConversationValidationError(f"Failed to serialize session metadata: {e}") from e

        try:
            with self._connection() as conn:
                with conn:
                    conn.execute(
                        """
                        INSERT INTO conversation_sessions (session_id, created_at, updated_at, status, title, metadata)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            session.session_id,
                            session.created_at.isoformat(),
                            session.updated_at.isoformat(),
                            session.status.value,
                            session.title,
                            metadata_str,
                        )
                    )
        except sqlite3.IntegrityError as e:
            raise ConversationValidationError(f"Session with ID {session.session_id} already exists: {e}") from e
        except sqlite3.Error as e:
            raise ConversationPersistenceError(f"Failed to create session: {e}") from e

    def get_session(self, session_id: str) -> ConversationSession | None:
        """Retrieves a conversation session by its ID."""
        try:
            with self._connection() as conn:
                cursor = conn.execute(
                    "SELECT session_id, created_at, updated_at, status, title, metadata FROM conversation_sessions WHERE session_id = ?",
                    (session_id,)
                )
                row = cursor.fetchone()
                if not row:
                    return None
                return self._row_to_session(row)
        except sqlite3.Error as e:
            raise ConversationPersistenceError(f"Failed to retrieve session: {e}") from e

    def list_sessions(self) -> List[ConversationSession]:
        """Lists all conversation sessions ordered by updated_at DESC."""
        try:
            with self._connection() as conn:
                cursor = conn.execute(
                    "SELECT session_id, created_at, updated_at, status, title, metadata FROM conversation_sessions ORDER BY updated_at DESC"
                )
                return [self._row_to_session(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise ConversationPersistenceError(f"Failed to list sessions: {e}") from e

    def update_session(self, session: ConversationSession) -> None:
        """Updates an existing session's metadata, title, status, etc."""
        if session.created_at.tzinfo is None or session.updated_at.tzinfo is None:
            raise ConversationValidationError("Datetime objects must be timezone-aware.")

        try:
            metadata_str = json.dumps(session.metadata)
        except (TypeError, ValueError) as e:
            raise ConversationValidationError(f"Failed to serialize session metadata: {e}") from e

        try:
            with self._connection() as conn:
                with conn:
                    cursor = conn.execute(
                        """
                        UPDATE conversation_sessions
                        SET created_at = ?, updated_at = ?, status = ?, title = ?, metadata = ?
                        WHERE session_id = ?
                        """,
                        (
                            session.created_at.isoformat(),
                            session.updated_at.isoformat(),
                            session.status.value,
                            session.title,
                            metadata_str,
                            session.session_id,
                        )
                    )
                    if cursor.rowcount == 0:
                        raise ConversationNotFoundError(f"Session {session.session_id} not found.")
        except sqlite3.Error as e:
            raise ConversationPersistenceError(f"Failed to update session: {e}") from e

    def close_session(self, session_id: str) -> None:
        """Marks a session as closed."""
        try:
            with self._connection() as conn:
                with conn:
                    # Check if session exists
                    cursor = conn.execute(
                        "SELECT status FROM conversation_sessions WHERE session_id = ?",
                        (session_id,)
                    )
                    row = cursor.fetchone()
                    if not row:
                        raise ConversationNotFoundError(f"Session {session_id} not found.")

                    conn.execute(
                        """
                        UPDATE conversation_sessions
                        SET status = ?, updated_at = ?
                        WHERE session_id = ?
                        """,
                        (
                            SessionStatus.CLOSED.value,
                            datetime.now(timezone.utc).isoformat(),
                            session_id,
                        )
                    )
        except ConversationError:
            raise
        except sqlite3.Error as e:
            raise ConversationPersistenceError(f"Failed to close session: {e}") from e

    def add_message(self, session_id: str, message: Message) -> None:
        """Adds a message to a session with transactional sequence allocation."""
        if message.timestamp.tzinfo is None:
            raise ConversationValidationError("Message timestamp must be timezone-aware.")
        if not message.content or not message.content.strip():
            raise ConversationValidationError("Message content must not be empty or whitespace-only.")

        try:
            metadata_str = json.dumps(message.metadata)
        except (TypeError, ValueError) as e:
            raise ConversationValidationError(f"Failed to serialize message metadata: {e}") from e

        try:
            with self._connection() as conn:
                with conn:
                    # 1. Verify session exists and is ACTIVE
                    cursor = conn.execute(
                        "SELECT status FROM conversation_sessions WHERE session_id = ?",
                        (session_id,)
                    )
                    row = cursor.fetchone()
                    if not row:
                        raise ConversationNotFoundError(f"Session {session_id} not found.")
                    
                    status = SessionStatus(row["status"])
                    if status == SessionStatus.CLOSED:
                        raise SessionStateError(f"Cannot add message to closed session {session_id}.")

                    # 2. Allocate sequence number
                    cursor = conn.execute(
                        "SELECT COALESCE(MAX(sequence_number), 0) + 1 FROM conversation_messages WHERE session_id = ?",
                        (session_id,)
                    )
                    seq_num = cursor.fetchone()[0]

                    # 3. Insert message
                    conn.execute(
                        """
                        INSERT INTO conversation_messages (message_id, session_id, role, content, timestamp, metadata, sequence_number)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            message.id,
                            session_id,
                            message.role.value,
                            message.content,
                            message.timestamp.isoformat(),
                            metadata_str,
                            seq_num,
                        )
                    )

                    # 4. Update session updated_at timestamp to match the message timestamp
                    conn.execute(
                        "UPDATE conversation_sessions SET updated_at = ? WHERE session_id = ?",
                        (message.timestamp.isoformat(), session_id)
                    )
        except sqlite3.IntegrityError as e:
            # UNIQUE constraint or FOREIGN KEY constraint violation
            if "FOREIGN KEY" in str(e):
                raise ConversationNotFoundError(f"Session {session_id} not found.") from e
            raise ConversationValidationError(f"Message conflict or duplicate message ID: {e}") from e
        except ConversationError:
            raise
        except sqlite3.Error as e:
            raise ConversationPersistenceError(f"Failed to add message: {e}") from e

    def get_messages(self, session_id: str) -> List[Message]:
        """Retrieves all messages for a session ordered by sequence_number ASC."""
        try:
            with self._connection() as conn:
                # First check if session exists to be explicit
                cursor = conn.execute(
                    "SELECT 1 FROM conversation_sessions WHERE session_id = ?",
                    (session_id,)
                )
                if not cursor.fetchone():
                    # Return empty list or raise? Let's return empty if not found, or raise.
                    # Wait, requirement: "retrieve messages" should work.
                    # If session does not exist, return empty list (just like memories retriever).
                    return []

                cursor = conn.execute(
                    """
                    SELECT message_id, role, content, timestamp, metadata
                    FROM conversation_messages
                    WHERE session_id = ?
                    ORDER BY sequence_number ASC
                    """,
                    (session_id,)
                )
                return [self._row_to_message(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise ConversationPersistenceError(f"Failed to retrieve messages: {e}") from e

    def count_messages(self, session_id: str) -> int:
        """Counts the total number of messages in a session."""
        try:
            with self._connection() as conn:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM conversation_messages WHERE session_id = ?",
                    (session_id,)
                )
                return cursor.fetchone()[0]
        except sqlite3.Error as e:
            raise ConversationPersistenceError(f"Failed to count messages: {e}") from e

    def _row_to_session(self, row: sqlite3.Row) -> ConversationSession:
        """Converts a SQLite database row to a ConversationSession domain model."""
        try:
            metadata_dict = json.loads(row["metadata"])
            if not isinstance(metadata_dict, dict):
                raise ConversationPersistenceError("Malformed metadata JSON in database.")
        except json.JSONDecodeError as e:
            raise ConversationPersistenceError(f"Failed to decode session metadata JSON: {e}") from e

        try:
            created_at = datetime.fromisoformat(row["created_at"])
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
        except ValueError as e:
            raise ConversationPersistenceError(f"Failed to parse created_at datetime: {e}") from e

        try:
            updated_at = datetime.fromisoformat(row["updated_at"])
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=timezone.utc)
        except ValueError as e:
            raise ConversationPersistenceError(f"Failed to parse updated_at datetime: {e}") from e

        try:
            status = SessionStatus(row["status"])
        except ValueError as e:
            raise ConversationPersistenceError(f"Invalid session status in database: {row['status']}") from e

        return ConversationSession(
            session_id=row["session_id"],
            created_at=created_at,
            updated_at=updated_at,
            status=status,
            title=row["title"],
            metadata=metadata_dict,
        )

    def _row_to_message(self, row: sqlite3.Row) -> Message:
        """Converts a SQLite database row to a Message domain model."""
        try:
            metadata_dict = json.loads(row["metadata"])
            if not isinstance(metadata_dict, dict):
                raise ConversationPersistenceError("Malformed metadata JSON in database.")
        except json.JSONDecodeError as e:
            raise ConversationPersistenceError(f"Failed to decode message metadata JSON: {e}") from e

        try:
            timestamp = datetime.fromisoformat(row["timestamp"])
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
        except ValueError as e:
            raise ConversationPersistenceError(f"Failed to parse timestamp datetime: {e}") from e

        try:
            role = MessageRole(row["role"])
        except ValueError as e:
            raise ConversationPersistenceError(f"Invalid message role in database: {row['role']}") from e

        return Message(
            id=row["message_id"],
            role=role,
            content=row["content"],
            timestamp=timestamp,
            metadata=metadata_dict,
        )
