"""Unit tests for memory resolution domain models."""

import pytest
from datetime import datetime, timezone
from dataclasses import FrozenInstanceError

from app.core.exceptions import MemoryValidationError
from app.memory.models import MemoryCandidate, MemoryType, MemorySource
from app.memory.resolution import (
    MemoryResolutionAction,
    MemoryResolutionDecision,
)


def create_test_candidate(content: str, memory_type: MemoryType = MemoryType.FACT) -> MemoryCandidate:
    """Helper to create a candidate memory for testing."""
    return MemoryCandidate(
        content=content,
        memory_type=memory_type,
        importance=0.8,
        confidence=0.9,
        source=MemorySource.USER,
        evidence="I live in Jaipur",
        metadata={}
    )


def test_decision_construction_valid_create():
    """Verify that a valid CREATE decision constructs successfully."""
    cand = create_test_candidate("The user lives in Jaipur.")
    decision = MemoryResolutionDecision(
        action=MemoryResolutionAction.CREATE,
        candidate=cand,
        target_memory_id=None,
        confidence=0.95,
        reason_code="NO_RELATED_MEMORY"
    )
    assert decision.action == MemoryResolutionAction.CREATE
    assert decision.candidate == cand
    assert decision.target_memory_id is None
    assert decision.confidence == 0.95
    assert decision.reason_code == "NO_RELATED_MEMORY"


def test_decision_construction_valid_update():
    """Verify that a valid UPDATE decision constructs successfully."""
    cand = create_test_candidate("The user prefers Python.")
    decision = MemoryResolutionDecision(
        action=MemoryResolutionAction.UPDATE,
        candidate=cand,
        target_memory_id="mem_123",
        confidence=0.92,
        reason_code="UPDATED_PREFERENCE"
    )
    assert decision.action == MemoryResolutionAction.UPDATE
    assert decision.target_memory_id == "mem_123"


def test_decision_construction_valid_replace():
    """Verify that a valid REPLACE decision constructs successfully."""
    cand = create_test_candidate("The user lives in Bangalore.")
    decision = MemoryResolutionDecision(
        action=MemoryResolutionAction.REPLACE,
        candidate=cand,
        target_memory_id="mem_456",
        confidence=0.98,
        reason_code="CHANGED_STATE"
    )
    assert decision.action == MemoryResolutionAction.REPLACE
    assert decision.target_memory_id == "mem_456"


def test_decision_construction_valid_keep_both():
    """Verify that a valid KEEP_BOTH decision constructs successfully."""
    cand = create_test_candidate("The user prefers Python.")
    decision = MemoryResolutionDecision(
        action=MemoryResolutionAction.KEEP_BOTH,
        candidate=cand,
        target_memory_id="mem_789",
        confidence=0.88,
        reason_code="DISTINCT_SCOPE"
    )
    assert decision.action == MemoryResolutionAction.KEEP_BOTH


def test_decision_construction_valid_ignore():
    """Verify that a valid IGNORE decision constructs successfully."""
    cand = create_test_candidate("The user's name is Anas.")
    decision = MemoryResolutionDecision(
        action=MemoryResolutionAction.IGNORE,
        candidate=cand,
        target_memory_id="mem_999",
        confidence=0.99,
        reason_code="SAME_DURABLE_CLAIM"
    )
    assert decision.action == MemoryResolutionAction.IGNORE


def test_decision_invalid_confidence():
    """Verify out-of-range confidence values are rejected."""
    cand = create_test_candidate("The user prefers Python.")
    with pytest.raises(MemoryValidationError):
        MemoryResolutionDecision(
            action=MemoryResolutionAction.CREATE,
            candidate=cand,
            target_memory_id=None,
            confidence=-0.1,
            reason_code="NO_RELATED_MEMORY"
        )

    with pytest.raises(MemoryValidationError):
        MemoryResolutionDecision(
            action=MemoryResolutionAction.CREATE,
            candidate=cand,
            target_memory_id=None,
            confidence=1.1,
            reason_code="NO_RELATED_MEMORY"
        )


def test_decision_invalid_reason_code():
    """Verify non-allowlisted reason codes are rejected."""
    cand = create_test_candidate("The user prefers Python.")
    with pytest.raises(MemoryValidationError):
        MemoryResolutionDecision(
            action=MemoryResolutionAction.CREATE,
            candidate=cand,
            target_memory_id=None,
            confidence=0.95,
            reason_code="INVALID_REASON_CODE"
        )


def test_decision_update_missing_target():
    """Verify UPDATE action without target ID is rejected."""
    cand = create_test_candidate("The user prefers Python.")
    with pytest.raises(MemoryValidationError):
        MemoryResolutionDecision(
            action=MemoryResolutionAction.UPDATE,
            candidate=cand,
            target_memory_id=None,
            confidence=0.95,
            reason_code="UPDATED_PREFERENCE"
        )


def test_decision_replace_missing_target():
    """Verify REPLACE action without target ID is rejected."""
    cand = create_test_candidate("The user prefers Python.")
    with pytest.raises(MemoryValidationError):
        MemoryResolutionDecision(
            action=MemoryResolutionAction.REPLACE,
            candidate=cand,
            target_memory_id=None,
            confidence=0.95,
            reason_code="CHANGED_STATE"
        )


def test_decision_create_with_target():
    """Verify CREATE action containing target ID is rejected."""
    cand = create_test_candidate("The user prefers Python.")
    with pytest.raises(MemoryValidationError):
        MemoryResolutionDecision(
            action=MemoryResolutionAction.CREATE,
            candidate=cand,
            target_memory_id="mem_123",
            confidence=0.95,
            reason_code="NO_RELATED_MEMORY"
        )


def test_decision_immutability():
    """Verify that MemoryResolutionDecision dataclass is frozen/immutable."""
    cand = create_test_candidate("The user prefers Python.")
    decision = MemoryResolutionDecision(
        action=MemoryResolutionAction.CREATE,
        candidate=cand,
        target_memory_id=None,
        confidence=0.95,
        reason_code="NO_RELATED_MEMORY"
    )
    with pytest.raises(FrozenInstanceError):
        decision.confidence = 0.99
