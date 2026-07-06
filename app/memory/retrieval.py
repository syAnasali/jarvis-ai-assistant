"""Deterministic lexical memory retriever implementation."""

import re
from typing import List, Set
from app.core.exceptions import MemoryValidationError, MemorySystemError
from app.memory.interfaces import MemoryRetriever, MemoryRepository
from app.memory.models import Memory, MemoryMatch, MemoryRetrievalResult

# Centralized constants for the Lexical Retriever
LEXICAL_THRESHOLD = 0.15
DEFAULT_LIMIT = 5

LEXICAL_QUERY_WEIGHT = 0.7
LEXICAL_MEMORY_WEIGHT = 0.3

RELEVANCE_LEXICAL_WEIGHT = 0.8
RELEVANCE_IMPORTANCE_WEIGHT = 0.2

STOP_WORDS = {"the", "a", "an", "is", "are", "of", "to", "for", "and"}


def normalize_text(text: str) -> List[str]:
    """Normalizes text by lowercasing, removing basic punctuation, and splitting.

    Args:
        text: The raw text string.

    Returns:
        List[str]: List of normalized tokens.
    """
    if not text:
        return []
    # Lowercase and strip punctuation using regex to preserve unicode alphanumeric chars
    cleaned = re.sub(r'[^\w\s]', '', text.lower())
    tokens = cleaned.split()
    # Filter empty tokens and basic stop-words
    return [t for t in tokens if t and t not in STOP_WORDS]


class LexicalMemoryRetriever(MemoryRetriever):
    """Deterministic local lexical memory retriever implementation."""

    def __init__(self, repository: MemoryRepository) -> None:
        """Initializes the retriever.

        Args:
            repository: Injected MemoryRepository persistence layer.
        """
        self._repository = repository

    def retrieve(self, query: str, limit: int = DEFAULT_LIMIT) -> MemoryRetrievalResult:
        """Searches long-term memories for records relevant to the query.

        Args:
            query: The search query string.
            limit: The maximum number of matches to return.

        Returns:
            MemoryRetrievalResult: Bounded matches and retrieval diagnostics.

        Raises:
            MemoryValidationError: If limit is invalid.
            MemorySystemError: If the database retrieval fails.
        """
        if limit <= 0:
            raise MemoryValidationError(f"Retrieval limit must be a positive integer, got {limit}")

        try:
            candidates = self._repository.list_all()
        except Exception as e:
            raise MemorySystemError(f"Failed to list memory candidates: {e}") from e

        query_tokens = set(normalize_text(query))
        total_candidates = len(candidates)

        if not query_tokens or total_candidates == 0:
            return MemoryRetrievalResult(
                query=query,
                matches=(),
                total_candidates=total_candidates,
                selected_count=0
            )

        matches = []
        for mem in candidates:
            mem_tokens = set(normalize_text(mem.content))
            if not mem_tokens:
                continue

            overlap_tokens = query_tokens & mem_tokens
            overlap_count = len(overlap_tokens)

            # Compute lexical score
            query_coverage = overlap_count / len(query_tokens)
            mem_coverage = overlap_count / len(mem_tokens)
            lexical_score = (LEXICAL_QUERY_WEIGHT * query_coverage) + (LEXICAL_MEMORY_WEIGHT * mem_coverage)

            # Skip if below relevance threshold
            if lexical_score < LEXICAL_THRESHOLD:
                continue

            # Compute final relevance score incorporating importance
            relevance_score = (RELEVANCE_LEXICAL_WEIGHT * lexical_score) + (RELEVANCE_IMPORTANCE_WEIGHT * mem.importance)

            matches.append(
                MemoryMatch(
                    memory=mem,
                    relevance_score=relevance_score,
                    lexical_score=lexical_score,
                    importance_score=mem.importance
                )
            )

        # Sort matches deterministically
        # Primary: relevance_score descending
        # Secondary: importance_score descending
        # Tertiary: updated_at timestamp descending
        # Quaternary: memory_id ascending
        def sort_key(match: MemoryMatch) -> tuple:
            return (
                -match.relevance_score,
                -match.importance_score,
                -match.memory.updated_at.timestamp(),
                match.memory.memory_id
            )

        matches.sort(key=sort_key)
        selected_matches = matches[:limit]

        return MemoryRetrievalResult(
            query=query,
            matches=tuple(selected_matches),
            total_candidates=total_candidates,
            selected_count=len(selected_matches)
        )
