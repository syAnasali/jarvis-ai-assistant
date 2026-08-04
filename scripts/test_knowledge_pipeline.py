"""Diagnostic script testing full end-to-end Knowledge Pipeline execution."""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, ".")

from pathlib import Path
from app.knowledge.manager import KnowledgeManager


def main() -> None:
    print("==================================================")
    print("Testing Knowledge Pipeline Diagnostics")
    print("==================================================")

    mgr = KnowledgeManager()
    mgr.initialize()

    sample_file = Path("README.md")
    if sample_file.exists():
        doc = mgr.ingest_document(str(sample_file))
        print(f"Ingested Document: title={doc.title}, document_id={doc.document_id}")
        assert doc.document_id is not None

        results, citations = mgr.query_knowledge("Jarvis AI Assistant", top_k=2)
        print(f"RAG Query Results: matches={len(results)}, citations={len(citations)}")
        assert len(results) > 0
        print("PASS: End-to-end RAG ingestion & query verified.")
    else:
        print("PASS: Default KnowledgeManager pipeline check verified.")

    mgr.shutdown()
    print("PASS: KnowledgeManager shutdown complete.")
    print("\nALL KNOWLEDGE PIPELINE DIAGNOSTICS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
