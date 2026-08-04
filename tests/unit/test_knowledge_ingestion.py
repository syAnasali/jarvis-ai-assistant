"""Unit tests for IngestionPipeline."""

import pytest
from app.knowledge.ingestion import IngestionPipeline
from app.knowledge.models import Document, DocumentFormat
from app.knowledge.repository import SQLiteKnowledgeRepository


def test_ingestion_pipeline_text_file(tmp_path):
    tf = tmp_path / "notes.md"
    tf.write_text("# RAG Research Notes\n\nVector databases and LLM context.", encoding="utf-8")

    repo = SQLiteKnowledgeRepository(database_path=":memory:")
    pipeline = IngestionPipeline(repository=repo)

    doc = pipeline.ingest_file(str(tf))
    assert isinstance(doc, Document)
    assert doc.format == DocumentFormat.MARKDOWN
    assert doc.title == "notes.md"
