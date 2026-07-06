"""Interfaces and abstract base classes for the memory subsystem."""

from abc import ABC, abstractmethod
from typing import List
from app.memory.models import Memory


class MemoryRepository(ABC):
    """Abstract base repository interface defining memory persistence operations."""

    @abstractmethod
    def add(self, memory: Memory) -> None:
        """Persists a new memory object.

        Args:
            memory: The Memory domain object to store.

        Raises:
            MemoryPersistenceError: If database execution fails.
            MemoryValidationError: If domain constraints are violated.
        """
        pass

    @abstractmethod
    def get(self, memory_id: str) -> Memory | None:
        """Retrieves a single memory by its unique identifier.

        Args:
            memory_id: The ID of the memory to find.

        Returns:
            Memory: The retrieved Memory object, or None if not found.

        Raises:
            MemoryPersistenceError: If database retrieval fails.
        """
        pass

    @abstractmethod
    def list_all(self) -> List[Memory]:
        """Retrieves all stored memories.

        Returns:
            List[Memory]: A list of all stored Memory objects.

        Raises:
            MemoryPersistenceError: If database retrieval fails.
        """
        pass

    @abstractmethod
    def update(self, memory: Memory) -> None:
        """Updates an existing memory with matching ID.

        Args:
            memory: The Memory domain object containing the updated state.

        Raises:
            MemoryNotFoundError: If no memory exists with the specified ID.
            MemoryPersistenceError: If the update operation fails.
            MemoryValidationError: If validation fails.
        """
        pass

    @abstractmethod
    def delete(self, memory_id: str) -> None:
        """Deletes a memory by its unique identifier.

        Args:
            memory_id: The unique identifier of the memory to delete.

        Raises:
            MemoryNotFoundError: If no memory exists with the specified ID.
            MemoryPersistenceError: If the deletion operation fails.
        """
        pass

    @abstractmethod
    def count(self) -> int:
        """Returns the total number of memories stored.

        Returns:
            int: The total memory count.

        Raises:
            MemoryPersistenceError: If count retrieval fails.
        """
        pass
