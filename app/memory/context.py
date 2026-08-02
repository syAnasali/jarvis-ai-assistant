"""Memory context construction utilities."""

from typing import List
from app.memory.models import MemoryMatch

MEMORY_CONTEXT_MARKER = "RELEVANT LONG-TERM MEMORY"

CONTEXT_INSTRUCTION = (
    "The following are relevant long-term memories retrieved from your storage. "
    "Use them only when relevant. Do not refer to your memory system or database to the user "
    "unnecessarily. If these memories conflict with current user instructions, prioritize the "
    "current instructions. Do not assert or claim uncertain information beyond the provided memories."
)


class MemoryContextBuilder:
    """Builds a structured prompt context from relevant memory matches."""

    def __init__(self, max_memories: int = 5, max_characters: int = 2000) -> None:
        """Initializes the context builder.

        Args:
            max_memories: The maximum number of memories to include in the context.
            max_characters: The maximum character count allowed for the context.
        """
        self._max_memories = max_memories
        self._max_characters = max_characters

    def deduplicate_and_filter(self, matches: List[MemoryMatch]) -> List[MemoryMatch]:
        """Deduplicates memories and filters out stale or duplicate entries.

        Args:
            matches: Input memory matches list.

        Returns:
            List[MemoryMatch]: Cleaned and deduplicated list of memory matches.
        """
        seen_contents = set()
        deduped: List[MemoryMatch] = []

        for match in matches:
            norm_content = match.memory.content.strip().lower()
            if norm_content in seen_contents:
                continue
            seen_contents.add(norm_content)
            deduped.append(match)

        return deduped

    def build(self, matches: List[MemoryMatch]) -> str:
        """Builds a formatted context string containing relevant memories.

        Args:
            matches: Sorted list of memory matches.

        Returns:
            str: Formatted memory context, or an empty string if no matches exist.
        """
        if not matches:
            return ""

        # Deduplicate and filter stale/duplicate memories
        cleaned_matches = self.deduplicate_and_filter(matches)

        # Enforce memory count bound
        target_matches = cleaned_matches[:self._max_memories]

        header = f"[{MEMORY_CONTEXT_MARKER}]\n{CONTEXT_INSTRUCTION}\n"
        current_len = len(header)
        facts = []

        for match in target_matches:
            fact_line = f"- {match.memory.content}"
            # Check length constraint including newline character
            next_len = len(fact_line) + 1
            if current_len + next_len > self._max_characters:
                # Stop cleanly and exclude the next memory
                break
            facts.append(fact_line)
            current_len += next_len

        if not facts:
            return ""

        return header + "\n".join(facts)
