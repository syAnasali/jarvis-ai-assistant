"""Unit tests for built-in knowledge tools."""

import pytest
from app.tools.builtin.knowledge import (
    IngestDocumentTool,
    SearchKnowledgeTool,
    SummarizeDocumentTool,
    ListDocumentsTool,
    RemoveDocumentTool,
)
from app.tools.models import ToolResult


def test_ingest_document_tool_execution(tmp_path):
    tf = tmp_path / "sample.txt"
    tf.write_text("Sample document text for ingestion.", encoding="utf-8")

    tool = IngestDocumentTool()
    res = tool.execute(file_path=str(tf))
    assert isinstance(res, ToolResult)
    assert res.success is True
    assert "document_id" in res.output


def test_search_knowledge_tool_execution(tmp_path):
    tf = tmp_path / "sample.txt"
    tf.write_text("Artificial Intelligence notes.", encoding="utf-8")

    tool_ingest = IngestDocumentTool()
    tool_ingest.execute(file_path=str(tf))

    tool_search = SearchKnowledgeTool(knowledge_manager=tool_ingest._manager)
    res = tool_search.execute(query="Artificial Intelligence")
    assert res.success is True
    assert "total_matches" in res.output


def test_list_documents_tool_execution():
    tool = ListDocumentsTool()
    res = tool.execute()
    assert res.success is True
    assert "total_documents" in res.output
