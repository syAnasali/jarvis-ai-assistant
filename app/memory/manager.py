"""Memory manager orchestrating the domain and repository layers."""

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List
from app.core.exceptions import MemoryNotFoundError, MemoryValidationError
from app.memory.interfaces import MemoryRepository
from app.memory.models import Memory, MemorySource, MemoryType
from app.utils.id_generator import generate_memory_id


class MemoryManager:
    """Manages memory lifecycle, validation, and persistence orchestration."""

    def __init__(self, repository: MemoryRepository) -> None:
        """Initializes the MemoryManager.

        Args:
            repository: Injected repository implementation for database persistence.
        """
        self._repository = repository

    def create_memory(
        self,
        content: str,
        memory_type: MemoryType,
        importance: float,
        source: MemorySource,
        metadata: Dict[str, Any] | None = None,
    ) -> Memory:
        """Validates and creates a new Memory domain object, persisting it.

        Args:
            content: Concise fact, preference, project, or context.
            memory_type: Semantic memory classification.
            importance: Priority score from 0.0 to 1.0.
            source: Source of memory creation.
            metadata: Extensible metadata dictionary.

        Returns:
            Memory: The newly created and stored Memory object.

        Raises:
            MemoryValidationError: If parameters fail validation constraints.
            MemoryPersistenceError: If storage operation fails.
        """
        # Validate metadata type upfront
        if metadata is not None and not isinstance(metadata, dict):
            raise MemoryValidationError("Memory metadata must be a dictionary.")

        # Copy metadata to prevent caller side-effects
        meta_copy = deepcopy(metadata) if metadata is not None else {}

        # Capture timezone-aware UTC timestamps
        now = datetime.now(timezone.utc)

        # Generate unique memory identifier
        memory_id = generate_memory_id()

        # Construct Memory (post_init validation runs automatically)
        memory = Memory(
            memory_id=memory_id,
            content=content,
            memory_type=memory_type,
            created_at=now,
            updated_at=now,
            importance=importance,
            source=source,
            metadata=meta_copy,
        )

        # Delegate storage to repository
        self._repository.add(memory)
        return memory

    def get_memory(self, memory_id: str) -> Memory | None:
        """Retrieves a single memory by ID.

        Args:
            memory_id: The ID of the memory to find.

        Returns:
            Memory: The stored memory, or None if not found.
        """
        return self._repository.get(memory_id)

    def list_memories(self) -> List[Memory]:
        """Lists all stored memories.

        Returns:
            List[Memory]: A list of stored memories.
        """
        return self._repository.list_all()

    def update_memory(
        self,
        memory_id: str,
        content: str | None = None,
        memory_type: MemoryType | None = None,
        importance: float | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> Memory:
        """Updates selective fields of an existing memory.

        Args:
            memory_id: Identifies the memory to update.
            content: Updated content string.
            memory_type: Updated memory category enum.
            importance: Updated importance score.
            metadata: Updated metadata dictionary.

        Returns:
            Memory: The updated Memory object.

        Raises:
            MemoryNotFoundError: If the ID does not match any stored memory.
            MemoryValidationError: If the updated fields fail constraints.
            MemoryPersistenceError: If database update fails.
        """
        original = self.get_memory(memory_id)
        if not original:
            raise MemoryNotFoundError(f"Memory with ID {memory_id} not found.")

        kwargs: Dict[str, Any] = {}
        if content is not None:
            kwargs["content"] = content
        if memory_type is not None:
            if not isinstance(memory_type, MemoryType):
                raise MemoryValidationError(f"Invalid memory type: {memory_type}")
            kwargs["memory_type"] = memory_type
        if importance is not None:
            kwargs["importance"] = importance
        if metadata is not None:
            if not isinstance(metadata, dict):
                raise MemoryValidationError("Memory metadata must be a dictionary.")
            kwargs["metadata"] = deepcopy(metadata)

        # Update modification timestamp to UTC now
        kwargs["updated_at"] = datetime.now(timezone.utc)

        # Use replace helper to obtain a new immutable instance
        from dataclasses import replace

        updated = replace(original, **kwargs)

        # Delegate update to persistence layer
        self._repository.update(updated)
        return updated

    def delete_memory(self, memory_id: str) -> None:
        """Deletes a memory by ID.

        Args:
            memory_id: The ID of the memory to delete.

        Raises:
            MemoryNotFoundError: If ID is not found.
            MemoryPersistenceError: If deletion fails.
        """
        self._repository.delete(memory_id)

    def count_memories(self) -> int:
        """Counts all stored memories.

        Returns:
            int: The total count of memories.
        """
        return self._repository.count()

    def replace_memory(self, old_memory_id: str, new_memory: Memory) -> Memory:
        """Atomically replaces an old memory with a new memory in persistence."""
        self._repository.replace(old_memory_id, new_memory)
        return new_memory
