"""Unit tests verifying vision-derived facts adhere to Memory safety and evidence rules."""

import pytest
from app.memory.validation import MemoryEvidenceValidator
from app.memory.models import MemoryCandidate, MemoryType, MemorySource
from app.vision.models import OCRResult


def test_vision_memory_evidence_rules_reject_raw_ocr():
    ocr = OCRResult(text="Raw arbitrary text block extracted from terminal 12345", confidence=0.8)
    
    # Create candidate representing raw arbitrary OCR output without first-person claim
    candidate = MemoryCandidate(
        content=ocr.text,
        memory_type=MemoryType.FACT,
        importance=0.5,
        confidence=ocr.confidence,
        source=MemorySource.SYSTEM,
        evidence=ocr.text
    )
    validator = MemoryEvidenceValidator()
    
    # Raw arbitrary OCR output without first-person indicator must fail validation (return False)
    is_valid = validator.validate(candidate, source_text=ocr.text)
    assert is_valid is False
