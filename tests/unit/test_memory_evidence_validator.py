"""Unit tests for the MemoryEvidenceValidator class."""

import pytest
from app.memory.models import MemoryCandidate, MemoryType, MemorySource
from app.memory.validation import MemoryEvidenceValidator


def create_candidate(content: str, evidence: str, memory_type: MemoryType = MemoryType.FACT) -> MemoryCandidate:
    return MemoryCandidate(
        content=content,
        memory_type=memory_type,
        importance=0.8,
        confidence=0.9,
        source=MemorySource.USER,
        evidence=evidence,
        metadata={}
    )


def test_validator_exact_evidence_accepted():
    """Verify that exact verbatim evidence is accepted."""
    validator = MemoryEvidenceValidator()
    cand = create_candidate("The user's name is Anas.", "My name is Anas.")
    assert validator.validate(cand, "Hello! My name is Anas. What's yours?") is True


def test_validator_whitespace_normalized_evidence_accepted():
    """Verify that whitespace variations in evidence are normalized and accepted."""
    validator = MemoryEvidenceValidator()
    cand = create_candidate("The user prefers Python.", "I   prefer   Python.")
    assert validator.validate(cand, "I prefer Python. It's awesome.") is True


def test_validator_missing_or_empty_evidence_rejected():
    """Verify that empty or invalid evidence strings are rejected."""
    validator = MemoryEvidenceValidator()
    
    # Empty string validation raises MemoryCandidateValidationError on candidate construction,
    # but we can verify validator returns False if we somehow bypass it or use empty source text.
    cand = create_candidate("The user prefers Python.", "I prefer Python.", MemoryType.PREFERENCE)
    assert validator.validate(cand, "") is False
    assert validator.validate(cand, "   ") is False


def test_validator_evidence_not_present_rejected():
    """Verify that evidence not present in the source text is rejected."""
    validator = MemoryEvidenceValidator()
    cand = create_candidate("The user prefers Python.", "I prefer Python.", MemoryType.PREFERENCE)
    assert validator.validate(cand, "I love writing code in C++.") is False


def test_validator_paraphrased_evidence_rejected():
    """Verify that paraphrased evidence (not matching verbatim) is rejected."""
    validator = MemoryEvidenceValidator()
    cand = create_candidate("The user prefers Python.", "My preferred programming language is Python", MemoryType.PREFERENCE)
    assert validator.validate(cand, "I prefer Python for personal projects.") is False


def test_validator_case_insensitive_matching():
    """Verify case-insensitive verbatim evidence is matched successfully."""
    validator = MemoryEvidenceValidator()
    cand = create_candidate("The user prefers Python.", "i prefer python", MemoryType.PREFERENCE)
    assert validator.validate(cand, "I prefer Python for my projects.") is True


def test_validator_source_and_candidate_not_mutated():
    """Verify that validation does not mutate candidate or source string."""
    validator = MemoryEvidenceValidator()
    source = "I prefer Python for my projects."
    cand = create_candidate("The user prefers Python.", "I prefer Python", MemoryType.PREFERENCE)
    
    validator.validate(cand, source)
    
    assert source == "I prefer Python for my projects."
    assert cand.evidence == "I prefer Python"
    assert cand.content == "The user prefers Python."


def test_validator_claim_support_conservatism():
    """Verify that task-local instructions without explicit preferences or projects are rejected."""
    validator = MemoryEvidenceValidator()
    
    # Preference rejected because no explicit preference indicator/first person reference
    cand_pref = create_candidate("The user prefers Python.", "Python", MemoryType.PREFERENCE)
    assert validator.validate(cand_pref, "Write a Python function to reverse a string.") is False

    # Preference rejected because no first person reference even if preference indicator matches
    cand_pref_no_fp = create_candidate("The user prefers Python.", "prefer Python", MemoryType.PREFERENCE)
    assert validator.validate(cand_pref_no_fp, "Users prefer Python over Java.") is False

    # Project rejected because no project indicator in evidence
    cand_proj = create_candidate("The user is building Jarvis.", "Jarvis", MemoryType.PROJECT)
    assert validator.validate(cand_proj, "I saw a movie called Jarvis.") is False

    # Project accepted when explicit project indicator and first-person references exist
    cand_proj_ok = create_candidate("The user is building Jarvis.", "I am building Jarvis", MemoryType.PROJECT)
    assert validator.validate(cand_proj_ok, "I am building Jarvis on weekends.") is True
