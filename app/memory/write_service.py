"""Memory write service coordinating candidate extraction and persistence."""

import re
import time
from typing import List
from app.core.exceptions import MemoryPersistenceError, MemorySystemError
from app.memory.interfaces import MemoryExtractor
from app.memory.models import MemoryCandidate, MemoryWriteResult, MemorySource
from app.memory.manager import MemoryManager
from app.memory.guard import SecretGuard
from app.memory.retrieval import normalize_text


def normalize_content(text: str) -> str:
    """Normalizes memory content for exact duplicate detection.

    Args:
        text: Raw content string.

    Returns:
        str: Normalized content.
    """
    if not text:
        return ""
    # Lowercase and strip whitespace
    t = text.lower().strip()
    # Replace repeated internal spaces
    t = re.sub(r"\s+", " ", t)
    # Remove basic terminal punctuation
    t = re.sub(r"[.,!?]+$", "", t)
    return t.strip()


from app.memory.validation import MemoryEvidenceValidator


class MemoryWriteService:
    """Coordinates memory extraction, duplicate checks, validation, and database writes."""

    def __init__(
        self,
        extractor: MemoryExtractor,
        memory_manager: MemoryManager,
        confidence_threshold: float = 0.8
    ) -> None:
        """Initializes the MemoryWriteService.

        Args:
            extractor: Injected MemoryExtractor implementation.
            memory_manager: Injected MemoryManager domain orchestrator.
            confidence_threshold: Minimum confidence required to persist memories.
        """
        self._extractor = extractor
        self._memory_manager = memory_manager
        self._confidence_threshold = confidence_threshold
        self._secret_guard = SecretGuard()
        self._evidence_validator = MemoryEvidenceValidator()

    def write_memories(self, text: str) -> MemoryWriteResult:
        """Extracts memories from user text, runs checks, and persists approved candidates.

        Args:
            text: Raw user message text.

        Returns:
            MemoryWriteResult: Stats showing counts and IDs of stored memories.

        Raises:
            MemorySystemError: If extraction fails or database listing fails.
            MemoryPersistenceError: If writing to the database fails.
        """
        start_time = time.perf_counter()

        extracted_count = 0
        persisted_count = 0
        duplicate_count = 0
        rejected_count = 0
        persisted_ids = []

        if not text or not text.strip():
            return MemoryWriteResult(0, 0, 0, 0, (), 0.0)

        try:
            # 1. Invoke MemoryExtractor
            extraction_result = self._extractor.extract(text)
            candidates = extraction_result.candidates
            extracted_count = len(candidates)
        except Exception as e:
            if isinstance(e, MemorySystemError):
                raise e
            raise MemorySystemError(f"Memory extraction failed: {e}") from e

        try:
            # List existing memories for duplicate check
            existing_memories = self._memory_manager.list_memories()
        except Exception as e:
            raise MemorySystemError(f"Failed to list existing memories: {e}") from e

        for candidate in candidates:
            # 1. Validate evidence
            if not self._evidence_validator.validate(candidate, text):
                rejected_count += 1
                continue

            # 2. Check confidence threshold
            if candidate.confidence < self._confidence_threshold:
                rejected_count += 1
                continue

            # 3. Secret guard check
            if self._secret_guard.contains_secret(candidate.content):
                rejected_count += 1
                continue

            # 4. Duplicate check primarily against memories of the same type
            same_type_memories = [m for m in existing_memories if m.memory_type == candidate.memory_type]
            
            is_duplicate = False
            cand_norm = normalize_content(candidate.content)

            # Exact normalized check
            for exist in same_type_memories:
                exist_norm = normalize_content(exist.content)
                if cand_norm == exist_norm:
                    is_duplicate = True
                    break

            if not is_duplicate:
                # Conservative Near-duplicate check:
                # High lexical similarity threshold with identical token sets requirement
                cand_tokens = set(normalize_text(candidate.content))
                for exist in same_type_memories:
                    exist_tokens = set(normalize_text(exist.content))
                    
                    overlap = len(cand_tokens & exist_tokens)
                    max_len = max(len(cand_tokens), len(exist_tokens))
                    similarity = overlap / max_len if max_len > 0 else 0.0
                    
                    if similarity >= 0.85 and cand_tokens == exist_tokens:
                        is_duplicate = True
                        break

            if is_duplicate:
                duplicate_count += 1
                continue

            # 5. Persist memory through MemoryManager
            try:
                meta = {
                    "extraction_method": "llm",
                    "source": "agent_request"
                }
                persisted = self._memory_manager.create_memory(
                    content=candidate.content,
                    memory_type=candidate.memory_type,
                    importance=candidate.importance,
                    source=MemorySource.USER,
                    metadata=meta
                )
                persisted_ids.append(persisted.memory_id)
                persisted_count += 1

                # Update existing memory cache for multi-candidate sibling duplicate checks
                existing_memories.append(persisted)
            except Exception as e:
                raise MemoryPersistenceError(f"Failed to persist candidate memory: {e}") from e

        duration_ms = (time.perf_counter() - start_time) * 1000
        return MemoryWriteResult(
            extracted_count=extracted_count,
            persisted_count=persisted_count,
            duplicate_count=duplicate_count,
            rejected_count=rejected_count,
            persisted_memory_ids=tuple(persisted_ids),
            duration_ms=duration_ms
        )
