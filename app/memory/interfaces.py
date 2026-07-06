from abc import ABC, abstractmethod
from typing import List
from app.memory.models import Memory, MemoryRetrievalResult, MemoryExtractionResult, MemoryCandidate


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

    def replace(self, old_memory_id: str, new_memory: Memory) -> None:
        """Atomically replaces an old memory with a new one.

        Args:
            old_memory_id: ID of the memory to replace/delete.
            new_memory: The new Memory object to persist.

        Raises:
            MemoryNotFoundError: If the old memory is not found.
            MemoryPersistenceError: If the database transaction fails.
            MemoryValidationError: If domain constraints of new_memory are violated.
        """
        raise NotImplementedError("replace method not implemented in this repository.")


class MemoryRetriever(ABC):
    """Abstract retriever interface defining memory search/matching operations."""

    @abstractmethod
    def retrieve(self, query: str, limit: int = 5) -> MemoryRetrievalResult:
        """Searches long-term memories for records relevant to the query.

        Args:
            query: The search query string.
            limit: The maximum number of matches to return.

        Returns:
            MemoryRetrievalResult: Bounded matches and retrieval diagnostics.

        Raises:
            MemorySystemError: If the retrieval process fails.
        """
        pass


class MemoryExtractor(ABC):
    """Abstract memory extractor interface defining semantic parsing of user inputs."""

    @abstractmethod
    def extract(self, text: str) -> MemoryExtractionResult:
        """Extracts candidate memory records from raw text.

        Args:
            text: The raw user message text.

        Returns:
            MemoryExtractionResult: Extracted candidates and source details.

        Raises:
            MemoryExtractionError: If the extraction model fails.
        """
        pass


class MemoryResolver(ABC):
    """Abstract interface defining memory conflict resolution operations."""

    @abstractmethod
    def resolve(
        self,
        candidate: MemoryCandidate,
        related_memories: List[Memory],
    ) -> "MemoryResolutionDecision":
        """Determines conflict resolution action between candidate and related memories.

        Args:
            candidate: The new MemoryCandidate being processed.
            related_memories: Existing memories related to the candidate.

        Returns:
            MemoryResolutionDecision: Resolution action and metadata.
        """
        pass
