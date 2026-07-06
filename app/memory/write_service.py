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
from app.memory.interfaces import MemoryResolver
from app.memory.related import RelatedMemoryFinder
from app.memory.resolution import (
    MemoryResolutionAction,
    MemoryResolutionDecision,
    MemoryResolutionValidator,
    MemoryResolutionExecutor,
)


class MemoryWriteService:
    """Coordinates memory extraction, duplicate checks, validation, and database writes."""

    def __init__(
        self,
        extractor: MemoryExtractor,
        memory_manager: MemoryManager,
        confidence_threshold: float = 0.8,
        related_finder: RelatedMemoryFinder | None = None,
        resolver: MemoryResolver | None = None,
        validator: MemoryResolutionValidator | None = None,
        executor: MemoryResolutionExecutor | None = None,
    ) -> None:
        """Initializes the MemoryWriteService.

        Args:
            extractor: Injected MemoryExtractor implementation.
            memory_manager: Injected MemoryManager domain orchestrator.
            confidence_threshold: Minimum confidence required to persist memories.
            related_finder: Prefilter to locate potentially related database memories.
            resolver: LLM conflict resolver interface.
            validator: Validator for resolution decisions.
            executor: Executor to apply resolution actions.
        """
        self._extractor = extractor
        self._memory_manager = memory_manager
        self._confidence_threshold = confidence_threshold
        self._secret_guard = SecretGuard()
        self._evidence_validator = MemoryEvidenceValidator()

        self._related_finder = related_finder or RelatedMemoryFinder()
        self._validator = validator or MemoryResolutionValidator()
        self._executor = executor or MemoryResolutionExecutor(memory_manager)

        self._resolver = resolver

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
        created_count = 0
        updated_count = 0
        replaced_count = 0
        kept_both_count = 0
        ignored_count = 0
        resolution_failed_count = 0

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

            # 5. Conflict Resolution Stage
            try:
                related = self._related_finder.find_related(candidate, existing_memories)
                
                if not related:
                    decision = MemoryResolutionDecision(
                        action=MemoryResolutionAction.CREATE,
                        candidate=candidate,
                        target_memory_id=None,
                        confidence=1.0,
                        reason_code="NO_RELATED_MEMORY"
                    )
                else:
                    if self._resolver:
                        decision = self._resolver.resolve(candidate, related)
                    else:
                        decision = MemoryResolutionDecision(
                            action=MemoryResolutionAction.CREATE,
                            candidate=candidate,
                            target_memory_id=None,
                            confidence=1.0,
                            reason_code="NO_RELATED_MEMORY"
                        )
                    
                    decision = self._validator.validate(decision, related)
            except Exception as e:
                resolution_failed_count += 1
                from app.core.logger import JarvisLogger
                JarvisLogger.get_logger("write_service").error(f"Failed resolving candidate memory: {e}")
                continue

            # Execute action (Persistence errors propagate here)
            try:
                res_id = self._executor.execute(decision)
            except Exception as e:
                if isinstance(e, MemoryPersistenceError):
                    raise e
                raise MemoryPersistenceError(f"Failed to persist candidate memory: {e}") from e
            
            # Update metrics
            if decision.action == MemoryResolutionAction.CREATE:
                created_count += 1
                persisted_count += 1
            elif decision.action == MemoryResolutionAction.KEEP_BOTH:
                kept_both_count += 1
                persisted_count += 1
            elif decision.action == MemoryResolutionAction.UPDATE:
                updated_count += 1
                persisted_count += 1
            elif decision.action == MemoryResolutionAction.REPLACE:
                replaced_count += 1
                persisted_count += 1
            elif decision.action == MemoryResolutionAction.IGNORE:
                ignored_count += 1
                if decision.reason_code == "UNSUPPORTED_RESOLUTION":
                    resolution_failed_count += 1
            
            if res_id:
                persisted_ids.append(res_id)
                # Refresh existing_memories cache
                new_mem = self._memory_manager.get_memory(res_id)
                if new_mem:
                    if decision.action in (MemoryResolutionAction.UPDATE, MemoryResolutionAction.REPLACE):
                        existing_memories = [m for m in existing_memories if m.memory_id != decision.target_memory_id]
                    existing_memories.append(new_mem)

        duration_ms = (time.perf_counter() - start_time) * 1000
        return MemoryWriteResult(
            extracted_count=extracted_count,
            persisted_count=persisted_count,
            duplicate_count=duplicate_count,
            rejected_count=rejected_count,
            persisted_memory_ids=tuple(persisted_ids),
            duration_ms=duration_ms,
            created_count=created_count,
            updated_count=updated_count,
            replaced_count=replaced_count,
            kept_both_count=kept_both_count,
            ignored_count=ignored_count,
            resolution_failed_count=resolution_failed_count
        )
