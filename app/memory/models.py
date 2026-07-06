"""Domain models for the memory subsystem."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any
from copy import deepcopy
from app.core.exceptions import MemoryValidationError, MemoryCandidateValidationError


class MemoryType(Enum):
    """Enumeration of standard memory classifications."""

    FACT = "FACT"
    PREFERENCE = "PREFERENCE"
    PROJECT = "PROJECT"
    CONTEXT = "CONTEXT"


class MemorySource(Enum):
    """Enumeration of standard memory origin sources."""

    USER = "USER"
    SYSTEM = "SYSTEM"
    MANUAL = "MANUAL"


@dataclass(frozen=True)
class Memory:
    """Domain model representing a concise, durable fact or user preference.

    Attributes:
        memory_id: Unique memory identifier.
        content: Concise statement of fact, preference, project, or context.
        memory_type: The semantic category of memory.
        created_at: Timezone-aware timestamp indicating memory creation.
        updated_at: Timezone-aware timestamp indicating last modification.
        importance: Score from 0.0 to 1.0 indicating rank/priority.
        source: The origin source of the memory.
        metadata: Extensible key-value dict storing additional attributes.
    """

    memory_id: str
    content: str
    memory_type: MemoryType
    created_at: datetime
    updated_at: datetime
    importance: float
    source: MemorySource
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Validate content
        if not isinstance(self.content, str):
            raise MemoryValidationError("Memory content must be a string.")
        if not self.content or not self.content.strip():
            raise MemoryValidationError("Memory content must not be empty or whitespace-only.")

        # Validate importance
        # We need to handle float type and range checks
        try:
            val = float(self.importance)
        except (ValueError, TypeError) as e:
            raise MemoryValidationError(f"Memory importance must be a numeric score, got {self.importance}") from e

        if val < 0.0 or val > 1.0:
            raise MemoryValidationError(f"Memory importance must be between 0.0 and 1.0, got {self.importance}")

        # Validate memory_type
        if not isinstance(self.memory_type, MemoryType):
            raise MemoryValidationError(f"Invalid memory type: {self.memory_type}")

        # Validate source
        if not isinstance(self.source, MemorySource):
            raise MemoryValidationError(f"Invalid memory source: {self.source}")

        # Validate timezone-aware datetime objects
        if not isinstance(self.created_at, datetime) or self.created_at.tzinfo is None:
            raise MemoryValidationError("created_at must be a timezone-aware datetime object.")
        if not isinstance(self.updated_at, datetime) or self.updated_at.tzinfo is None:
            raise MemoryValidationError("updated_at must be a timezone-aware datetime object.")

        # Validate metadata
        if not isinstance(self.metadata, dict):
            raise MemoryValidationError("Memory metadata must be a dictionary.")


@dataclass(frozen=True)
class MemoryMatch:
    """Represents a matched memory with calculated relevance scores.

    Attributes:
        memory: The matched Memory domain object.
        relevance_score: Combined final scoring from 0.0 to 1.0.
        lexical_score: Pure text overlap scoring from 0.0 to 1.0.
        importance_score: Bounded importance score from 0.0 to 1.0.
    """

    memory: Memory
    relevance_score: float
    lexical_score: float
    importance_score: float


@dataclass(frozen=True)
class MemoryRetrievalResult:
    """Result payload returned by memory retrieval operations.

    Attributes:
        query: The normalized user request string.
        matches: Immutable tuple of matched memories.
        total_candidates: Count of Candidate memories evaluated.
        selected_count: Count of matched memories returned.
    """

    query: str
    matches: tuple[MemoryMatch, ...]
    total_candidates: int
    selected_count: int


@dataclass(frozen=True)
class MemoryCandidate:
    """Domain model representing a structured candidate for long-term memory.

    Attributes:
        content: Concise statement of fact, preference, project, or context.
        memory_type: The semantic category of memory.
        importance: Score from 0.0 to 1.0 indicating priority/rank.
        confidence: Score from 0.0 to 1.0 indicating extraction confidence.
        source: The origin source of the memory.
        metadata: Extensible key-value dict storing additional attributes.
    """

    content: str
    memory_type: MemoryType
    importance: float
    confidence: float
    source: MemorySource
    evidence: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.content, str):
            raise MemoryCandidateValidationError("Memory content must be a string.")
        if not self.content or not self.content.strip():
            raise MemoryCandidateValidationError("Memory content must not be empty or whitespace-only.")

        if not isinstance(self.evidence, str):
            raise MemoryCandidateValidationError("Memory candidate evidence must be a string.")
        if not self.evidence or not self.evidence.strip():
            raise MemoryCandidateValidationError("Memory candidate evidence must not be empty or whitespace-only.")

        try:
            imp = float(self.importance)
        except (ValueError, TypeError) as e:
            raise MemoryCandidateValidationError(f"Memory importance must be a numeric score, got {self.importance}") from e
        if imp < 0.0 or imp > 1.0:
            raise MemoryCandidateValidationError(f"Memory importance must be between 0.0 and 1.0, got {self.importance}")

        try:
            conf = float(self.confidence)
        except (ValueError, TypeError) as e:
            raise MemoryCandidateValidationError(f"Memory confidence must be a numeric score, got {self.confidence}") from e
        if conf < 0.0 or conf > 1.0:
            raise MemoryCandidateValidationError(f"Memory confidence must be between 0.0 and 1.0, got {self.confidence}")

        if not isinstance(self.memory_type, MemoryType):
            raise MemoryCandidateValidationError(f"Invalid memory type: {self.memory_type}")

        if not isinstance(self.source, MemorySource):
            raise MemoryCandidateValidationError(f"Invalid memory source: {self.source}")

        if not isinstance(self.metadata, dict):
            raise MemoryCandidateValidationError("Memory metadata must be a dictionary.")

        object.__setattr__(self, "metadata", deepcopy(self.metadata))


@dataclass(frozen=True)
class MemoryExtractionResult:
    """Immutable result model returned by memory extraction operations.

    Attributes:
        candidates: Immutable tuple of extracted MemoryCandidate objects.
        source_text: The original user request text string.
        candidate_count: Number of candidate memories extracted.
    """

    candidates: tuple[MemoryCandidate, ...]
    source_text: str
    candidate_count: int


@dataclass(frozen=True)
class MemoryWriteResult:
    """Immutable result model returned by memory write operations.

    Attributes:
        extracted_count: Total candidates extracted.
        persisted_count: Total memories successfully persisted.
        duplicate_count: Total duplicates detected and rejected.
        rejected_count: Total memories rejected (e.g. low confidence or secrets).
        persisted_memory_ids: Immutable tuple of IDs of newly persisted memories.
        duration_ms: Total duration of the extraction and write process in milliseconds.
    """

    extracted_count: int
    persisted_count: int
    duplicate_count: int
    rejected_count: int
    persisted_memory_ids: tuple[str, ...]
    duration_ms: float = 0.0
    created_count: int = 0
    updated_count: int = 0
    replaced_count: int = 0
    kept_both_count: int = 0
    ignored_count: int = 0
    resolution_failed_count: int = 0
