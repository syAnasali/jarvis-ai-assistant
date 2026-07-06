"""Deterministic prefilter to find potentially related memories for conflict resolution."""

from typing import List
from app.memory.models import Memory, MemoryCandidate
from app.memory.retrieval import normalize_text


class RelatedMemoryFinder:
    """Finds a bounded list of potentially related memories using token-based lexical overlap."""

    def __init__(self, limit: int = 5) -> None:
        """Initializes the RelatedMemoryFinder.

        Args:
            limit: The maximum number of related memories to return.
        """
        self._limit = limit

    def find_related(self, candidate: MemoryCandidate, existing_memories: List[Memory]) -> List[Memory]:
        """Inspects existing memories and returns a bounded, sorted list of potentially related memories.

        The scoring is determined by:
        1. Jaccard similarity of normalized tokens (excluding basic stopwords).
        2. A boost if they share the same MemoryType.
        3. Memory importance score as a tie-breaker.

        Args:
            candidate: The new MemoryCandidate to evaluate.
            existing_memories: A list of all active Memory objects in the database.

        Returns:
            List[Memory]: Up to `limit` related memories sorted in descending order of relevance.
        """
        if not existing_memories:
            return []

        low_info_words = {"user", "users", "user's", "assistant", "assistants", "assistant's"}
        cand_tokens = set(normalize_text(candidate.content)) - low_info_words
        if not cand_tokens:
            return []

        scored_memories = []
        for mem in existing_memories:
            mem_tokens = set(normalize_text(mem.content)) - low_info_words
            if not mem_tokens:
                continue

            intersection = cand_tokens & mem_tokens
            union = cand_tokens | mem_tokens
            jaccard = len(intersection) / len(union) if union else 0.0

            # Boost for same memory type
            same_type_boost = 0.1 if mem.memory_type == candidate.memory_type else 0.0

            score = jaccard + same_type_boost

            # Keep only if there is at least some overlap or same type compatibility
            if score > 0.0:
                scored_memories.append((score, mem.importance, mem))

        # Sort by score desc, then by importance desc (tie-breaker), ensuring deterministic ordering
        scored_memories.sort(key=lambda x: (x[0], x[1]), reverse=True)

        # Return only the Memory objects, bounded by limit
        return [item[2] for item in scored_memories[:self._limit]]
