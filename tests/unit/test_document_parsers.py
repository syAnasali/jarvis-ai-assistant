"""Unit tests for UnifiedDocumentParser."""

import pytest
from pathlib import Path
from app.knowledge.parser import UnifiedDocumentParser, DocumentParseError
from app.knowledge.models import DocumentFormat


def test_unified_document_parser_can_parse():
    parser = UnifiedDocumentParser()
    assert parser.can_parse("notes.txt") is True
    assert parser.can_parse("document.pdf") is True
    assert parser.can_parse("script.py") is True


def test_unified_document_parser_plain_text(tmp_path):
    parser = UnifiedDocumentParser()
    tf = tmp_path / "test.txt"
    tf.write_text("Plain text content for RAG indexing.", encoding="utf-8")

    doc = parser.parse(str(tf))
    assert doc.format == DocumentFormat.TXT
    assert doc.raw_content == "Plain text content for RAG indexing."


def test_unified_document_parser_nonexistent_file():
    parser = UnifiedDocumentParser()
    with pytest.raises(DocumentParseError):
        parser.parse("nonexistent_file_path_12345.xyz")
