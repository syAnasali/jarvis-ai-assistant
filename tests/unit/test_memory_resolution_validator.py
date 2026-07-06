"""Unit tests for MemoryResolutionValidator."""

import pytest
from datetime import datetime, timezone

from app.memory.models import Memory, MemoryCandidate, MemoryType, MemorySource
from app.memory.resolution import (
    MemoryResolutionAction,
    MemoryResolutionDecision,
    MemoryResolutionValidator,
)


def create_test_candidate(content: str) -> MemoryCandidate:
    """Helper to create candidate memories."""
    return MemoryCandidate(
        content=content,
        memory_type=MemoryType.PREFERENCE,
        importance=0.8,
        confidence=0.9,
        source=MemorySource.USER,
        evidence="I prefer Python",
        metadata={}
    )


def create_test_memory(memory_id: str, content: str) -> Memory:
    """Helper to create active memories."""
    return Memory(
        memory_id=memory_id,
        content=content,
        memory_type=MemoryType.PREFERENCE,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        importance=0.8,
        source=MemorySource.USER,
        metadata={}
    )


def test_validator_create_accepted():
    """Verify CREATE is accepted without any target memory."""
    validator = MemoryResolutionValidator()
    cand = create_test_candidate("The user prefers Python.")
    decision = MemoryResolutionDecision(
        action=MemoryResolutionAction.CREATE,
        candidate=cand,
        target_memory_id=None,
        confidence=0.95,
        reason_code="NO_RELATED_MEMORY"
    )
    validated = validator.validate(decision, [])
    assert validated.action == MemoryResolutionAction.CREATE
    assert validated.target_memory_id is None


def test_validator_update_accepted_with_valid_target():
    """Verify UPDATE is accepted when target memory exists in related list."""
    validator = MemoryResolutionValidator()
    cand = create_test_candidate("The user prefers JavaScript.")
    target = create_test_memory("mem_123", "The user prefers Python.")
    
    decision = MemoryResolutionDecision(
        action=MemoryResolutionAction.UPDATE,
        candidate=cand,
        target_memory_id="mem_123",
        confidence=0.95,
        reason_code="UPDATED_PREFERENCE"
    )
    validated = validator.validate(decision, [target])
    assert validated.action == MemoryResolutionAction.UPDATE
    assert validated.target_memory_id == "mem_123"


def test_validator_replace_accepted_with_valid_target():
    """Verify REPLACE is accepted when target memory exists in related list."""
    validator = MemoryResolutionValidator()
    cand = create_test_candidate("The user lives in Bangalore.")
    target = create_test_memory("mem_456", "The user lives in Jaipur.")
    
    decision = MemoryResolutionDecision(
        action=MemoryResolutionAction.REPLACE,
        candidate=cand,
        target_memory_id="mem_456",
        confidence=0.98,
        reason_code="CHANGED_STATE"
    )
    validated = validator.validate(decision, [target])
    assert validated.action == MemoryResolutionAction.REPLACE
    assert validated.target_memory_id == "mem_456"


def test_validator_target_not_in_related_rejected():
    """Verify resolver decisions targeting unknown memory IDs are rejected and downgraded to IGNORE."""
    validator = MemoryResolutionValidator()
    cand = create_test_candidate("The user prefers JavaScript.")
    # Target memory in DB
    target_in_db = create_test_memory("mem_123", "The user prefers Python.")
    
    # Decision targets "mem_999" (not supplied as related)
    decision = MemoryResolutionDecision(
        action=MemoryResolutionAction.UPDATE,
        candidate=cand,
        target_memory_id="mem_999",
        confidence=0.95,
        reason_code="UPDATED_PREFERENCE"
    )
    validated = validator.validate(decision, [target_in_db])
    # Should fall back to IGNORE to prevent targeting arbitrary/unseen memories
    assert validated.action == MemoryResolutionAction.IGNORE
    assert validated.reason_code == "UNSUPPORTED_RESOLUTION"


def test_validator_low_confidence_update_downgraded():
    """Verify destructive actions (UPDATE) with low confidence (< 0.90) are downgraded to KEEP_BOTH."""
    # Threshold 0.90, confidence 0.85
    validator = MemoryResolutionValidator(destructive_confidence_threshold=0.90)
    cand = create_test_candidate("The user prefers JavaScript.")
    target = create_test_memory("mem_123", "The user prefers Python.")
    
    decision = MemoryResolutionDecision(
        action=MemoryResolutionAction.UPDATE,
        candidate=cand,
        target_memory_id="mem_123",
        confidence=0.85,
        reason_code="UPDATED_PREFERENCE"
    )
    validated = validator.validate(decision, [target])
    # Downgrades to KEEP_BOTH so we preserve both instead of deleting old one
    assert validated.action == MemoryResolutionAction.KEEP_BOTH
    assert validated.reason_code == "INSUFFICIENT_CONFLICT_EVIDENCE"


def test_validator_low_confidence_replace_downgraded():
    """Verify destructive actions (REPLACE) with low confidence (< 0.90) are downgraded to KEEP_BOTH."""
    validator = MemoryResolutionValidator(destructive_confidence_threshold=0.90)
    cand = create_test_candidate("The user lives in Bangalore.")
    target = create_test_memory("mem_456", "The user lives in Jaipur.")
    
    decision = MemoryResolutionDecision(
        action=MemoryResolutionAction.REPLACE,
        candidate=cand,
        target_memory_id="mem_456",
        confidence=0.89,
        reason_code="CHANGED_STATE"
    )
    validated = validator.validate(decision, [target])
    assert validated.action == MemoryResolutionAction.KEEP_BOTH
    assert validated.reason_code == "INSUFFICIENT_CONFLICT_EVIDENCE"


def test_validator_keep_both_and_ignore_accepted():
    """Verify KEEP_BOTH and IGNORE decisions bypass destructive confidence checks."""
    validator = MemoryResolutionValidator(destructive_confidence_threshold=0.90)
    cand = create_test_candidate("The user likes Java.")
    target = create_test_memory("mem_123", "The user prefers Python.")
    
    decision = MemoryResolutionDecision(
        action=MemoryResolutionAction.KEEP_BOTH,
        candidate=cand,
        target_memory_id="mem_123",
        confidence=0.75, # low confidence is ok for non-destructive actions
        reason_code="DISTINCT_SCOPE"
    )
    validated = validator.validate(decision, [target])
    assert validated.action == MemoryResolutionAction.KEEP_BOTH
