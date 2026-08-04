"""Diagnostic script testing citation formatting and clickable file URL generation."""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, ".")

from app.knowledge.citations import StructuredCitationFormatter
from app.knowledge.models import DocumentChunk, RetrievalResult


def main() -> None:
    print("==================================================")
    print("Testing Citation Formatting Diagnostics")
    print("==================================================")

    formatter = StructuredCitationFormatter()
    chunk = DocumentChunk(
        document_id="doc1",
        content="AI Research Notes on Neural Networks",
        chunk_index=0,
        page_number=12,
        start_line=3,
        metadata={"file_path": "C:\\Docs\\AI_Notes.pdf"}
    )
    res = RetrievalResult(chunk=chunk, score=0.95)

    citations = formatter.format_citations([res])
    print(f"Citations Formatted: count={len(citations)}")
    assert len(citations) == 1
    cit = citations[0]
    print(f"Citation: title={cit.document_title}, page={cit.page_number}, url={cit.file_url}")
    assert cit.file_url.startswith("file://")
    assert cit.page_number == 12
    print("PASS: Citation formatting & file:/// URLs verified.")

    print("\nALL CITATION DIAGNOSTICS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
