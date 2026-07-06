"""Memory resolution domain models, parser, validator, and executor."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Set
import json
from copy import deepcopy
from datetime import datetime, timezone

from app.core.exceptions import MemoryValidationError, MemoryNotFoundError
from app.memory.models import Memory, MemoryCandidate, MemorySource
from app.memory.manager import MemoryManager
from app.utils.id_generator import generate_memory_id


class MemoryResolutionAction(Enum):
    """Enumeration of memory conflict resolution actions."""

    CREATE = "CREATE"
    UPDATE = "UPDATE"
    REPLACE = "REPLACE"
    KEEP_BOTH = "KEEP_BOTH"
    IGNORE = "IGNORE"


# Controlled allowlist of resolution reason codes
RESOLUTION_REASON_CODES: Set[str] = {
    "NO_RELATED_MEMORY",
    "SAME_DURABLE_CLAIM",
    "UPDATED_PREFERENCE",
    "UPDATED_FACT",
    "CHANGED_STATE",
    "DISTINCT_SCOPE",
    "DISTINCT_PROJECT",
    "INSUFFICIENT_CONFLICT_EVIDENCE",
    "OBSOLETE_MEMORY",
    "UNSUPPORTED_RESOLUTION",
}


@dataclass(frozen=True)
class MemoryResolutionDecision:
    """Immutable resolution decision mapping a candidate to a database action.

    Attributes:
        action: The resolution action to take.
        candidate: The MemoryCandidate being resolved.
        target_memory_id: Target memory ID if updating or replacing.
        confidence: Model/resolver confidence in the resolution decision (0.0 to 1.0).
        reason_code: Controlled reason classification code.
    """

    action: MemoryResolutionAction
    candidate: MemoryCandidate
    target_memory_id: str | None
    confidence: float
    reason_code: str

    def __post_init__(self) -> None:
        # Validate action type
        if not isinstance(self.action, MemoryResolutionAction):
            raise MemoryValidationError(f"Invalid resolution action: {self.action}")

        # Validate candidate type
        if not isinstance(self.candidate, MemoryCandidate):
            raise MemoryValidationError("candidate must be an instance of MemoryCandidate.")

        # Validate confidence range
        try:
            conf = float(self.confidence)
        except (ValueError, TypeError) as e:
            raise MemoryValidationError(f"Resolution confidence must be a numeric score, got {self.confidence}") from e
        if conf < 0.0 or conf > 1.0:
            raise MemoryValidationError(f"Resolution confidence must be between 0.0 and 1.0, got {self.confidence}")

        # Validate reason code
        if self.reason_code not in RESOLUTION_REASON_CODES:
            raise MemoryValidationError(f"Invalid resolution reason_code: {self.reason_code}")

        # Validate target ID constraints
        if self.action in (MemoryResolutionAction.UPDATE, MemoryResolutionAction.REPLACE):
            if not self.target_memory_id or not isinstance(self.target_memory_id, str) or not self.target_memory_id.strip():
                raise MemoryValidationError(f"Action {self.action.value} requires a valid target_memory_id.")
        elif self.action == MemoryResolutionAction.CREATE:
            if self.target_memory_id is not None:
                raise MemoryValidationError("Action CREATE must not have a target_memory_id.")


class MemoryResolutionParser:
    """Safely extracts and parses JSON resolution outputs from models."""

    @staticmethod
    def parse(output_text: str, candidate: MemoryCandidate) -> MemoryResolutionDecision:
        """Parses LLM output into a MemoryResolutionDecision, failing conservatively to IGNORE.

        Args:
            output_text: Raw output string from the LLM.
            candidate: The candidate memory being resolved.

        Returns:
            MemoryResolutionDecision: The parsed decision, or a conservative IGNORE decision on failure.
        """
        fallback_decision = MemoryResolutionDecision(
            action=MemoryResolutionAction.IGNORE,
            candidate=candidate,
            target_memory_id=None,
            confidence=0.0,
            reason_code="UNSUPPORTED_RESOLUTION",
        )

        if not output_text or not output_text.strip():
            return fallback_decision

        # Extract JSON block if fenced
        cleaned = output_text.strip()
        if "```" in cleaned:
            # Simple markdown extraction
            lines = cleaned.splitlines()
            json_lines = []
            in_json = False
            for line in lines:
                if line.strip().startswith("```"):
                    if in_json:
                        break
                    else:
                        in_json = True
                        continue
                if in_json:
                    json_lines.append(line)
            if json_lines:
                cleaned = "\n".join(json_lines).strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            return fallback_decision

        if not isinstance(data, dict):
            return fallback_decision

        # Validate required fields
        if "action" not in data or "confidence" not in data or "reason_code" not in data:
            return fallback_decision

        try:
            # Map action string to Enum
            action_str = str(data["action"]).upper()
            action = MemoryResolutionAction(action_str)
        except ValueError:
            return fallback_decision

        reason_code = str(data["reason_code"]).upper()
        if reason_code not in RESOLUTION_REASON_CODES:
            return fallback_decision

        try:
            confidence = float(data["confidence"])
        except (ValueError, TypeError):
            return fallback_decision

        target_memory_id = data.get("target_memory_id")
        if target_memory_id is not None:
            target_memory_id = str(target_memory_id).strip()
            if not target_memory_id:
                target_memory_id = None

        try:
            return MemoryResolutionDecision(
                action=action,
                candidate=candidate,
                target_memory_id=target_memory_id,
                confidence=confidence,
                reason_code=reason_code,
            )
        except MemoryValidationError:
            return fallback_decision


class MemoryResolutionValidator:
    """Enforces correctness of resolution decisions against the supplied related memories context."""

    def __init__(self, destructive_confidence_threshold: float = 0.90) -> None:
        """Initializes the validator.

        Args:
            destructive_confidence_threshold: Confidence required for destructive actions (UPDATE, REPLACE).
        """
        self._destructive_confidence_threshold = destructive_confidence_threshold

    def validate(
        self,
        decision: MemoryResolutionDecision,
        related_memories: List[Memory],
    ) -> MemoryResolutionDecision:
        """Validates decision constraints and applies destructive confidence fallback.

        Args:
            decision: The parsed resolution decision.
            related_memories: Bounded list of related memories supplied to the resolver.

        Returns:
            MemoryResolutionDecision: Validated decision, potentially downgraded conservatively.
        """
        # 1. Resolver cannot target memory outside the supplied related set
        related_ids = {m.memory_id for m in related_memories}

        if decision.action in (MemoryResolutionAction.UPDATE, MemoryResolutionAction.REPLACE):
            if decision.target_memory_id not in related_ids:
                # Target memory ID doesn't match any supplied memory. Conservative fallback is IGNORE.
                return MemoryResolutionDecision(
                    action=MemoryResolutionAction.IGNORE,
                    candidate=decision.candidate,
                    target_memory_id=None,
                    confidence=0.0,
                    reason_code="UNSUPPORTED_RESOLUTION",
                )

            # 2. Destructive confidence threshold check
            if decision.confidence < self._destructive_confidence_threshold:
                # Downgrade destructive action to KEEP_BOTH.
                # KEEP_BOTH allows referencing a target ID but will not mutate it.
                return MemoryResolutionDecision(
                    action=MemoryResolutionAction.KEEP_BOTH,
                    candidate=decision.candidate,
                    target_memory_id=decision.target_memory_id,
                    confidence=decision.confidence,
                    reason_code="INSUFFICIENT_CONFLICT_EVIDENCE",
                )

        return decision


class MemoryResolutionExecutor:
    """Executes validated resolution decisions using MemoryManager and Repository APIs."""

    def __init__(self, memory_manager: MemoryManager) -> None:
        """Initializes the executor.

        Args:
            memory_manager: Injected MemoryManager orchestrator.
        """
        self._memory_manager = memory_manager

    def execute(self, decision: MemoryResolutionDecision) -> str | None:
        """Executes the action determined by the resolution decision.

        Args:
            decision: The validated resolution decision.

        Returns:
            str | None: The memory ID of the created, updated, or replaced memory,
                        or None if IGNORE action.
        """
        action = decision.action
        candidate = decision.candidate

        if action == MemoryResolutionAction.IGNORE:
            return None

        if action in (MemoryResolutionAction.CREATE, MemoryResolutionAction.KEEP_BOTH):
            # Create a new memory from candidate
            meta = {
                "extraction_method": "llm",
                "source": "agent_request",
            }
            if candidate.metadata:
                meta.update(candidate.metadata)
            meta["last_resolution_action"] = action.value
            persisted = self._memory_manager.create_memory(
                content=candidate.content,
                memory_type=candidate.memory_type,
                importance=candidate.importance,
                source=MemorySource.USER,
                metadata=meta,
            )
            return persisted.memory_id

        if action == MemoryResolutionAction.UPDATE:
            # Update target memory with candidate values
            target_id = decision.target_memory_id
            if not target_id:
                raise MemoryValidationError("UPDATE action missing target ID.")

            original = self._memory_manager.get_memory(target_id)
            if not original:
                raise MemoryNotFoundError(f"Memory with ID {target_id} not found.")

            meta = deepcopy(original.metadata)
            meta["last_resolution_action"] = "UPDATE"

            # Merge updated content and metadata, keeping created_at
            updated = self._memory_manager.update_memory(
                memory_id=target_id,
                content=candidate.content,
                memory_type=candidate.memory_type,
                importance=candidate.importance,
                metadata=meta,
            )
            return updated.memory_id

        if action == MemoryResolutionAction.REPLACE:
            # Atomically delete old and create new memory
            target_id = decision.target_memory_id
            if not target_id:
                raise MemoryValidationError("REPLACE action missing target ID.")

            original = self._memory_manager.get_memory(target_id)
            if not original:
                raise MemoryNotFoundError(f"Memory with ID {target_id} not found.")

            now = datetime.now(timezone.utc)
            new_id = generate_memory_id()
            meta = {
                "extraction_method": "llm",
                "source": "agent_request",
            }
            if candidate.metadata:
                meta.update(candidate.metadata)
            meta["last_resolution_action"] = "REPLACE"

            new_memory = Memory(
                memory_id=new_id,
                content=candidate.content,
                memory_type=candidate.memory_type,
                created_at=now,
                updated_at=now,
                importance=candidate.importance,
                source=MemorySource.USER,
                metadata=meta,
            )

            # Atomically replace old memory with the new one
            self._memory_manager.replace_memory(target_id, new_memory)
            return new_id

        return None
