"""Unit tests for StructuredCitationFormatter."""

import pytest
from app.knowledge.citations import StructuredCitationFormatter
from app.knowledge.models import DocumentChunk, RetrievalResult, Citation


def test_citation_formatting():
    formatter = StructuredCitationFormatter()
    chunk = DocumentChunk(
        document_id="d1",
        content="Sample content snippet",
        chunk_index=0,
        page_number=5,
        metadata={"file_path": "C:\\Docs\\paper.pdf"}
    )
    res = RetrievalResult(chunk=chunk, score=0.9)

    citations = formatter.format_citations([res])
    assert len(citations) == 1
    cit = citations[0]
    assert cit.document_title == "paper.pdf"
    assert cit.file_url.startswith("file://")
    assert cit.page_number == 5
