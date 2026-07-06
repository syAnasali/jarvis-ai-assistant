"""Unit tests for MemoryResolutionParser."""

import pytest
from datetime import datetime, timezone

from app.memory.models import MemoryCandidate, MemoryType, MemorySource
from app.memory.resolution import (
    MemoryResolutionAction,
    MemoryResolutionDecision,
    MemoryResolutionParser,
)


def create_test_candidate() -> MemoryCandidate:
    """Helper to create a candidate memory for testing."""
    return MemoryCandidate(
        content="The user prefers Python.",
        memory_type=MemoryType.PREFERENCE,
        importance=0.8,
        confidence=0.9,
        source=MemorySource.USER,
        evidence="I prefer Python",
        metadata={}
    )


def test_parser_valid_create():
    """Verify parsing a valid CREATE action from JSON."""
    cand = create_test_candidate()
    json_text = '{"action": "CREATE", "target_memory_id": null, "confidence": 0.98, "reason_code": "NO_RELATED_MEMORY"}'
    decision = MemoryResolutionParser.parse(json_text, cand)
    assert decision.action == MemoryResolutionAction.CREATE
    assert decision.target_memory_id is None
    assert decision.confidence == 0.98
    assert decision.reason_code == "NO_RELATED_MEMORY"


def test_parser_valid_update():
    """Verify parsing a valid UPDATE action from JSON."""
    cand = create_test_candidate()
    json_text = '{"action": "UPDATE", "target_memory_id": "mem_123", "confidence": 0.96, "reason_code": "UPDATED_PREFERENCE"}'
    decision = MemoryResolutionParser.parse(json_text, cand)
    assert decision.action == MemoryResolutionAction.UPDATE
    assert decision.target_memory_id == "mem_123"
    assert decision.confidence == 0.96
    assert decision.reason_code == "UPDATED_PREFERENCE"


def test_parser_valid_replace():
    """Verify parsing a valid REPLACE action from JSON."""
    cand = create_test_candidate()
    json_text = '{"action": "REPLACE", "target_memory_id": "mem_456", "confidence": 0.95, "reason_code": "CHANGED_STATE"}'
    decision = MemoryResolutionParser.parse(json_text, cand)
    assert decision.action == MemoryResolutionAction.REPLACE
    assert decision.target_memory_id == "mem_456"
    assert decision.confidence == 0.95
    assert decision.reason_code == "CHANGED_STATE"


def test_parser_markdown_fenced():
    """Verify parser strips markdown fences and extracts JSON."""
    cand = create_test_candidate()
    json_text = "```json\n" '{"action": "KEEP_BOTH", "target_memory_id": null, "confidence": 0.93, "reason_code": "DISTINCT_SCOPE"}\n' "```"
    decision = MemoryResolutionParser.parse(json_text, cand)
    assert decision.action == MemoryResolutionAction.KEEP_BOTH
    assert decision.confidence == 0.93
    assert decision.reason_code == "DISTINCT_SCOPE"


def test_parser_malformed_json_fallback():
    """Verify parser falls back to IGNORE on malformed JSON."""
    cand = create_test_candidate()
    json_text = "{malformed json text}"
    decision = MemoryResolutionParser.parse(json_text, cand)
    assert decision.action == MemoryResolutionAction.IGNORE
    assert decision.confidence == 0.0
    assert decision.reason_code == "UNSUPPORTED_RESOLUTION"


def test_parser_unknown_action_fallback():
    """Verify parser falls back to IGNORE on unknown action value."""
    cand = create_test_candidate()
    json_text = '{"action": "DESTROY", "target_memory_id": "mem_123", "confidence": 0.95, "reason_code": "UPDATED_PREFERENCE"}'
    decision = MemoryResolutionParser.parse(json_text, cand)
    assert decision.action == MemoryResolutionAction.IGNORE


def test_parser_unknown_reason_code_fallback():
    """Verify parser falls back to IGNORE on unknown reason code."""
    cand = create_test_candidate()
    json_text = '{"action": "UPDATE", "target_memory_id": "mem_123", "confidence": 0.95, "reason_code": "UNKNOWN_CODE"}'
    decision = MemoryResolutionParser.parse(json_text, cand)
    assert decision.action == MemoryResolutionAction.IGNORE


def test_parser_missing_fields_fallback():
    """Verify parser falls back to IGNORE on missing required JSON fields."""
    cand = create_test_candidate()
    json_text = '{"action": "UPDATE", "confidence": 0.95}'
    decision = MemoryResolutionParser.parse(json_text, cand)
    assert decision.action == MemoryResolutionAction.IGNORE


def test_parser_out_of_bounds_confidence_fallback():
    """Verify parser falls back to IGNORE if confidence is out of bounds."""
    cand = create_test_candidate()
    json_text = '{"action": "UPDATE", "target_memory_id": "mem_123", "confidence": 1.5, "reason_code": "UPDATED_PREFERENCE"}'
    decision = MemoryResolutionParser.parse(json_text, cand)
    assert decision.action == MemoryResolutionAction.IGNORE


def test_parser_missing_required_target_id():
    """Verify parser falls back to IGNORE if target ID is missing/null on UPDATE."""
    cand = create_test_candidate()
    json_text = '{"action": "UPDATE", "target_memory_id": null, "confidence": 0.95, "reason_code": "UPDATED_PREFERENCE"}'
    decision = MemoryResolutionParser.parse(json_text, cand)
    assert decision.action == MemoryResolutionAction.IGNORE
