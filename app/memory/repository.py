"""SQLite-backed memory repository implementation."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, List
from app.config.settings import settings
from app.core.exceptions import (
    MemoryNotFoundError,
    MemoryPersistenceError,
    MemoryValidationError,
)
from app.memory.interfaces import MemoryRepository
from app.memory.models import Memory, MemorySource, MemoryType


class SQLiteMemoryRepository(MemoryRepository):
    """SQLite implementation of the MemoryRepository interface."""

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
        try:
            # Ensure database directory exists
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(self._db_path))
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            yield conn
        except sqlite3.Error as e:
            raise MemoryPersistenceError(f"Failed to connect to database: {e}") from e
        finally:
            if "conn" in locals():
                conn.close()

    def _init_db(self) -> None:
        """Creates the memories table if it does not already exist."""
        try:
            with self._connection() as conn:
                with conn:
                    conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS memories (
                            memory_id TEXT PRIMARY KEY,
                            content TEXT NOT NULL,
                            memory_type TEXT NOT NULL,
                            created_at TEXT NOT NULL,
                            updated_at TEXT NOT NULL,
                            importance REAL NOT NULL,
                            source TEXT NOT NULL,
                            metadata TEXT NOT NULL,
                            CONSTRAINT chk_importance CHECK (importance >= 0.0 AND importance <= 1.0),
                            CONSTRAINT chk_content CHECK (length(trim(content)) > 0)
                        )
                        """
                    )
        except sqlite3.Error as e:
            raise MemoryPersistenceError(f"Failed to initialize database schema: {e}") from e

    def _row_to_memory(self, row: sqlite3.Row) -> Memory:
        """Converts a SQLite database row to a Memory domain model.

        Raises:
            MemoryPersistenceError: If database formatting is corrupted.
        """
        try:
            metadata_dict = json.loads(row["metadata"])
            if not isinstance(metadata_dict, dict):
                raise MemoryPersistenceError("Malformed metadata JSON in database.")
        except json.JSONDecodeError as e:
            raise MemoryPersistenceError(f"Failed to decode memory metadata JSON: {e}") from e

        try:
            created_at = datetime.fromisoformat(row["created_at"])
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
        except ValueError as e:
            raise MemoryPersistenceError(f"Failed to parse created_at datetime: {e}") from e

        try:
            updated_at = datetime.fromisoformat(row["updated_at"])
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=timezone.utc)
        except ValueError as e:
            raise MemoryPersistenceError(f"Failed to parse updated_at datetime: {e}") from e

        try:
            memory_type = MemoryType(row["memory_type"])
        except ValueError as e:
            raise MemoryPersistenceError(f"Invalid memory_type in database: {row['memory_type']}") from e

        try:
            source = MemorySource(row["source"])
        except ValueError as e:
            raise MemoryPersistenceError(f"Invalid source in database: {row['source']}") from e

        return Memory(
            memory_id=row["memory_id"],
            content=row["content"],
            memory_type=memory_type,
            created_at=created_at,
            updated_at=updated_at,
            importance=row["importance"],
            source=source,
            metadata=metadata_dict,
        )

    def add(self, memory: Memory) -> None:
        """Persists a new memory object."""
        try:
            with self._connection() as conn:
                with conn:
                    conn.execute(
                        """
                        INSERT INTO memories (
                            memory_id, content, memory_type, created_at, updated_at, importance, source, metadata
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            memory.memory_id,
                            memory.content,
                            memory.memory_type.value,
                            memory.created_at.isoformat(),
                            memory.updated_at.isoformat(),
                            memory.importance,
                            memory.source.value,
                            json.dumps(memory.metadata),
                        ),
                    )
        except sqlite3.IntegrityError as e:
            raise MemoryValidationError(f"Database constraint violation on add: {e}") from e
        except sqlite3.Error as e:
            raise MemoryPersistenceError(f"Database execution error on add: {e}") from e

    def get(self, memory_id: str) -> Memory | None:
        """Retrieves a single memory by its unique identifier."""
        try:
            with self._connection() as conn:
                row = conn.execute(
                    "SELECT * FROM memories WHERE memory_id = ?", (memory_id,)
                ).fetchone()
                if not row:
                    return None
                return self._row_to_memory(row)
        except sqlite3.Error as e:
            raise MemoryPersistenceError(f"Database execution error on get: {e}") from e

    def list_all(self) -> List[Memory]:
        """Retrieves all stored memories."""
        try:
            with self._connection() as conn:
                rows = conn.execute("SELECT * FROM memories").fetchall()
                return [self._row_to_memory(row) for row in rows]
        except sqlite3.Error as e:
            raise MemoryPersistenceError(f"Database execution error on list_all: {e}") from e

    def update(self, memory: Memory) -> None:
        """Updates an existing memory with matching ID."""
        try:
            with self._connection() as conn:
                with conn:
                    cursor = conn.execute(
                        """
                        UPDATE memories SET
                            content = ?,
                            memory_type = ?,
                            updated_at = ?,
                            importance = ?,
                            metadata = ?
                        WHERE memory_id = ?
                        """,
                        (
                            memory.content,
                            memory.memory_type.value,
                            memory.updated_at.isoformat(),
                            memory.importance,
                            json.dumps(memory.metadata),
                            memory.memory_id,
                        ),
                    )
                    if cursor.rowcount == 0:
                        raise MemoryNotFoundError(f"Memory with ID {memory.memory_id} not found.")
        except sqlite3.IntegrityError as e:
            raise MemoryValidationError(f"Database constraint violation on update: {e}") from e
        except sqlite3.Error as e:
            raise MemoryPersistenceError(f"Database execution error on update: {e}") from e

    def delete(self, memory_id: str) -> None:
        """Deletes a memory by its unique identifier."""
        try:
            with self._connection() as conn:
                with conn:
                    cursor = conn.execute(
                        "DELETE FROM memories WHERE memory_id = ?", (memory_id,)
                    )
                    if cursor.rowcount == 0:
                        raise MemoryNotFoundError(f"Memory with ID {memory_id} not found.")
        except sqlite3.Error as e:
            raise MemoryPersistenceError(f"Database execution error on delete: {e}") from e

    def count(self) -> int:
        """Returns the total number of memories stored."""
        try:
            with self._connection() as conn:
                row = conn.execute("SELECT COUNT(*) FROM memories").fetchone()
                return row[0] if row else 0
        except sqlite3.Error as e:
            raise MemoryPersistenceError(f"Database execution error on count: {e}") from e
