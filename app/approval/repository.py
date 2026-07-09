"""SQLite repository implementation for persistent action approvals."""

import json
import sqlite3
from abc import ABC, abstractmethod
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, List, Optional
from app.config.settings import settings
from app.core.exceptions import ApprovalPersistenceError
from app.core.logger import JarvisLogger
from app.approval.models import PendingAction, PendingActionStatus
from app.tools.models import ToolPermission

logger = JarvisLogger.get_logger("approval_repository")


class ApprovalRepository(ABC):
    """Abstract base repository contract for action approvals."""

    @abstractmethod
    def add(self, action: PendingAction) -> None:
        """Persists a new PendingAction."""
        pass

    @abstractmethod
    def get(self, action_id: str) -> Optional[PendingAction]:
        """Retrieves a PendingAction by ID."""
        pass

    @abstractmethod
    def update_status(self, action_id: str, status: PendingActionStatus) -> None:
        """Updates the status of a PendingAction."""
        pass

    @abstractmethod
    def list_pending(self) -> List[PendingAction]:
        """Lists all pending approval actions."""
        pass

    @abstractmethod
    def expire_actions(self, now: datetime) -> int:
        """Transitions PENDING actions past expires_at to EXPIRED. Returns count."""
        pass

    @abstractmethod
    def atomic_consume(self, action_id: str) -> bool:
        """Atomically transitions an APPROVED action to EXECUTED.

        Returns True if successful, False if already consumed or not approved.
        """
        pass


class SQLiteApprovalRepository(ApprovalRepository):
    """SQLite-backed implementation of the ApprovalRepository interface."""

    def __init__(self, database_path: Path | None = None) -> None:
        """Initializes the SQLite approval repository and sets up tables.

        Args:
            database_path: Optional file path for the SQLite database.
        """
        self._db_path = database_path or settings.database_path
        self._init_db()

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Provides a database connection within a safe context manager."""
        try:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(self._db_path))
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            yield conn
        except sqlite3.Error as e:
            raise ApprovalPersistenceError(f"Failed to connect to database: {e}") from e
        finally:
            if "conn" in locals():
                conn.close()

    def _init_db(self) -> None:
        """Creates the pending_actions table if it does not exist."""
        try:
            with self._connection() as conn:
                with conn:
                    conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS pending_actions (
                            action_id TEXT PRIMARY KEY,
                            tool_name TEXT NOT NULL,
                            arguments TEXT NOT NULL,
                            permission_level TEXT NOT NULL,
                            status TEXT NOT NULL,
                            created_at TEXT NOT NULL,
                            expires_at TEXT NOT NULL,
                            reason TEXT NOT NULL,
                            request_id TEXT,
                            session_id TEXT,
                            metadata TEXT NOT NULL
                        )
                        """
                    )
                    # Index for querying pending or expired actions efficiently
                    conn.execute(
                        "CREATE INDEX IF NOT EXISTS idx_action_status_expiry ON pending_actions(status, expires_at);"
                    )
        except sqlite3.Error as e:
            raise ApprovalPersistenceError(f"Failed to initialize approval schema: {e}") from e

    def _row_to_model(self, row: sqlite3.Row) -> PendingAction:
        """Converts a database row into a PendingAction, handling corrupted JSON safely."""
        try:
            arguments = json.loads(row["arguments"])
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Failed to deserialize arguments JSON for action {row['action_id']}: {e}")
            arguments = {}

        try:
            metadata = json.loads(row["metadata"])
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Failed to deserialize metadata JSON for action {row['action_id']}: {e}")
            metadata = {}

        try:
            created_at = datetime.fromisoformat(row["created_at"])
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
        except Exception:
            created_at = datetime.now(timezone.utc)

        try:
            expires_at = datetime.fromisoformat(row["expires_at"])
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
        except Exception:
            expires_at = datetime.now(timezone.utc)

        return PendingAction(
            action_id=row["action_id"],
            tool_name=row["tool_name"],
            arguments=arguments,
            permission_level=ToolPermission(row["permission_level"]),
            status=PendingActionStatus(row["status"]),
            created_at=created_at,
            expires_at=expires_at,
            reason=row["reason"],
            request_id=row["request_id"],
            session_id=row["session_id"],
            metadata=metadata
        )

    def add(self, action: PendingAction) -> None:
        try:
            arguments_str = json.dumps(action.arguments)
            metadata_str = json.dumps(action.metadata)
        except (TypeError, ValueError) as e:
            raise ApprovalPersistenceError(f"Failed to serialize action data: {e}") from e

        try:
            with self._connection() as conn:
                with conn:
                    conn.execute(
                        """
                        INSERT INTO pending_actions (
                            action_id, tool_name, arguments, permission_level, status,
                            created_at, expires_at, reason, request_id, session_id, metadata
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            action.action_id,
                            action.tool_name,
                            arguments_str,
                            action.permission_level.value,
                            action.status.value,
                            action.created_at.isoformat(),
                            action.expires_at.isoformat(),
                            action.reason,
                            action.request_id,
                            action.session_id,
                            metadata_str
                        )
                    )
        except sqlite3.Error as e:
            raise ApprovalPersistenceError(f"Failed to save pending action: {e}") from e

    def get(self, action_id: str) -> Optional[PendingAction]:
        try:
            with self._connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM pending_actions WHERE action_id = ?",
                    (action_id,)
                )
                row = cursor.fetchone()
                if row:
                    return self._row_to_model(row)
                return None
        except sqlite3.Error as e:
            raise ApprovalPersistenceError(f"Failed to load pending action: {e}") from e

    def update_status(self, action_id: str, status: PendingActionStatus) -> None:
        try:
            with self._connection() as conn:
                with conn:
                    conn.execute(
                        "UPDATE pending_actions SET status = ? WHERE action_id = ?",
                        (status.value, action_id)
                    )
        except sqlite3.Error as e:
            raise ApprovalPersistenceError(f"Failed to update action status: {e}") from e

    def list_pending(self) -> List[PendingAction]:
        try:
            with self._connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM pending_actions WHERE status = ?",
                    (PendingActionStatus.PENDING.value,)
                )
                return [self._row_to_model(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise ApprovalPersistenceError(f"Failed to list pending actions: {e}") from e

    def expire_actions(self, now: datetime) -> int:
        try:
            with self._connection() as conn:
                with conn:
                    cursor = conn.execute(
                        """
                        UPDATE pending_actions
                        SET status = ?
                        WHERE status = ? AND expires_at < ?
                        """,
                        (
                            PendingActionStatus.EXPIRED.value,
                            PendingActionStatus.PENDING.value,
                            now.isoformat()
                        )
                    )
                    return cursor.rowcount
        except sqlite3.Error as e:
            raise ApprovalPersistenceError(f"Failed to expire pending actions: {e}") from e

    def atomic_consume(self, action_id: str) -> bool:
        try:
            with self._connection() as conn:
                with conn:
                    cursor = conn.execute(
                        """
                        UPDATE pending_actions
                        SET status = ?
                        WHERE action_id = ? AND status = ?
                        """,
                        (
                            PendingActionStatus.EXECUTED.value,
                            action_id,
                            PendingActionStatus.APPROVED.value
                        )
                    )
                    return cursor.rowcount == 1
        except sqlite3.Error as e:
            raise ApprovalPersistenceError(f"Failed to atomically consume action: {e}") from e
