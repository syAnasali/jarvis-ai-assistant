"""Unit tests for the MemoryExtractionParser class."""

import pytest
from app.core.exceptions import MemoryExtractionError
from app.memory.models import MemoryType, MemorySource
from app.memory.parser import MemoryExtractionParser


def test_parser_valid_single_candidate():
    """Verify a single valid candidate JSON parses successfully."""
    parser = MemoryExtractionParser()
    raw = """
    {
      "memories": [
        {
          "content": "The user prefers Python.",
          "memory_type": "PREFERENCE",
          "importance": 0.8,
          "confidence": 0.95,
          "evidence": "I prefer Python."
        }
      ]
    }
    """
    candidates = parser.parse(raw)
    assert len(candidates) == 1
    c = candidates[0]
    assert c.content == "The user prefers Python."
    assert c.memory_type == MemoryType.PREFERENCE
    assert c.importance == 0.8
    assert c.confidence == 0.95
    assert c.source == MemorySource.USER
    assert c.evidence == "I prefer Python."


def test_parser_valid_multiple_candidates():
    """Verify multiple valid candidates are all parsed successfully."""
    parser = MemoryExtractionParser()
    raw = """
    {
      "memories": [
        {
          "content": "Fact A",
          "memory_type": "FACT",
          "importance": 0.5,
          "confidence": 0.8,
          "evidence": "A"
        },
        {
          "content": "Pref B",
          "memory_type": "PREFERENCE",
          "importance": 0.6,
          "confidence": 0.9,
          "evidence": "B"
        }
      ]
    }
    """
    candidates = parser.parse(raw, source=MemorySource.MANUAL)
    assert len(candidates) == 2
    assert candidates[0].content == "Fact A"
    assert candidates[1].content == "Pref B"
    assert candidates[0].source == MemorySource.MANUAL
    assert candidates[0].evidence == "A"


def test_parser_invalid_json():
    """Verify malformed JSON raises MemoryExtractionError."""
    parser = MemoryExtractionParser()
    with pytest.raises(MemoryExtractionError, match="Invalid JSON format"):
        parser.parse("invalid-json{")


def test_parser_missing_memories_key():
    """Verify JSON without 'memories' key raises MemoryExtractionError."""
    parser = MemoryExtractionParser()
    raw = '{"facts": []}'
    with pytest.raises(MemoryExtractionError, match="Missing required top-level key 'memories'"):
        parser.parse(raw)


def test_parser_memories_not_list():
    """Verify non-list memories value raises MemoryExtractionError."""
    parser = MemoryExtractionParser()
    raw = '{"memories": "not a list"}'
    with pytest.raises(MemoryExtractionError, match="'memories' key must map to a JSON array/list"):
        parser.parse(raw)


def test_parser_malformed_candidate_skipped():
    """Verify malformed candidates are safely skipped without failing overall parsing."""
    parser = MemoryExtractionParser()
    raw = """
    {
      "memories": [
        {
          "memory_type": "FACT"
        }
      ]
    }
    """
    candidates = parser.parse(raw)
    assert len(candidates) == 0


def test_parser_valid_survives_malformed_siblings():
    """Verify valid entries are parsed even if sibling entries are malformed."""
    parser = MemoryExtractionParser()
    raw = """
    {
      "memories": [
        {
          "memory_type": "FACT"
        },
        {
          "content": "Valid fact",
          "memory_type": "FACT",
          "importance": 0.5,
          "confidence": 0.8,
          "evidence": "Valid fact"
        }
      ]
    }
    """
    candidates = parser.parse(raw)
    assert len(candidates) == 1
    assert candidates[0].content == "Valid fact"


def test_parser_invalid_memory_type_rejected():
    """Verify invalid memory type values are skipped."""
    parser = MemoryExtractionParser()
    raw = """
    {
      "memories": [
        {
          "content": "Valid content",
          "memory_type": "INVALID_TYPE",
          "importance": 0.5,
          "confidence": 0.8,
          "evidence": "Valid content"
        }
      ]
    }
    """
    candidates = parser.parse(raw)
    assert len(candidates) == 0


def test_parser_importance_out_of_range_rejected():
    """Verify importance scores outside [0.0, 1.0] are skipped."""
    parser = MemoryExtractionParser()
    raw_below = '{"memories": [{"content": "A", "memory_type": "FACT", "importance": -0.1, "evidence": "A"}]}'
    raw_above = '{"memories": [{"content": "B", "memory_type": "FACT", "importance": 1.1, "evidence": "B"}]}'
    
    assert len(parser.parse(raw_below)) == 0
    assert len(parser.parse(raw_above)) == 0


def test_parser_confidence_out_of_range_rejected():
    """Verify confidence scores outside [0.0, 1.0] are skipped."""
    parser = MemoryExtractionParser()
    raw_below = '{"memories": [{"content": "A", "memory_type": "FACT", "confidence": -0.1, "evidence": "A"}]}'
    raw_above = '{"memories": [{"content": "B", "memory_type": "FACT", "confidence": 1.1, "evidence": "B"}]}'
    
    assert len(parser.parse(raw_below)) == 0
    assert len(parser.parse(raw_above)) == 0


def test_parser_whitespace_normalized():
    """Verify trailing and multiple internal spaces are normalized."""
    parser = MemoryExtractionParser()
    raw = """
    {
      "memories": [
        {
          "content": "  The   user   prefers    Python.  ",
          "memory_type": "PREFERENCE",
          "importance": 0.5,
          "confidence": 0.8,
          "evidence": "I prefer Python"
        }
      ]
    }
    """
    candidates = parser.parse(raw)
    assert len(candidates) == 1
    assert candidates[0].content == "The user prefers Python."


def test_parser_evidence_required_and_validated():
    """Verify parser rejects candidates with missing, empty, or wrong type evidence."""
    parser = MemoryExtractionParser()
    
    # Missing evidence key
    raw_missing = """
    {
      "memories": [
        {
          "content": "Pref A",
          "memory_type": "PREFERENCE",
          "importance": 0.8,
          "confidence": 0.95
        }
      ]
    }
    """
    assert len(parser.parse(raw_missing)) == 0

    # Empty evidence key
    raw_empty = """
    {
      "memories": [
        {
          "content": "Pref A",
          "memory_type": "PREFERENCE",
          "importance": 0.8,
          "confidence": 0.95,
          "evidence": ""
        }
      ]
    }
    """
    assert len(parser.parse(raw_empty)) == 0

    # Wrong type evidence key (int instead of string)
    raw_wrong_type = """
    {
      "memories": [
        {
          "content": "Pref A",
          "memory_type": "PREFERENCE",
          "importance": 0.8,
          "confidence": 0.95,
          "evidence": 12345
        }
      ]
    }
    """
    assert len(parser.parse(raw_wrong_type)) == 0
