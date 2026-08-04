"""Unit tests for Knowledge Voice Integration."""

import pytest
from app.knowledge.manager import KnowledgeManager


def test_voice_query_generates_answer_and_citations(tmp_path):
    tf = tmp_path / "os_notes.txt"
    tf.write_text("Operating Systems: Processes, Threads, Virtual Memory, and File Systems.", encoding="utf-8")

    mgr = KnowledgeManager()
    mgr.initialize()
    mgr.ingest_document(str(tf))

    results, citations = mgr.query_knowledge("Summarize operating systems notes")
    assert len(results) >= 1
    assert len(citations) >= 1
    assert citations[0].file_url.startswith("file://")

    mgr.shutdown()
