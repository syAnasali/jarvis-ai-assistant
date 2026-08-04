"""Additional comprehensive unit tests for Personal Knowledge Base (RAG) subsystem."""

import pytest
from app.knowledge.models import (
    DocumentFormat,
    ChunkStrategy,
    Document,
    DocumentChunk,
    KnowledgeQuery,
    RetrievalResult,
    Citation,
    IndexStatus,
)
from app.knowledge.parser import UnifiedDocumentParser
from app.knowledge.chunker import ConfigurableTextChunker
from app.knowledge.embeddings import LocalHashEmbeddingProvider
from app.knowledge.repository import SQLiteKnowledgeRepository
from app.knowledge.index import LocalVectorStore
from app.knowledge.retriever import HybridRetrieverEngine
from app.knowledge.reranker import ResultRerankerEngine
from app.knowledge.citations import StructuredCitationFormatter
from app.knowledge.manager import KnowledgeManager
from app.tools.builtin.knowledge import (
    IngestDocumentTool,
    SearchKnowledgeTool,
    SummarizeDocumentTool,
    ListDocumentsTool,
    RemoveDocumentTool,
)


def test_document_format_enum_values():
    assert DocumentFormat.PDF.value == "PDF"
    assert DocumentFormat.DOCX.value == "DOCX"
    assert DocumentFormat.MARKDOWN.value == "MARKDOWN"
    assert DocumentFormat.CODE.value == "CODE"


def test_chunk_strategy_enum_values():
    assert ChunkStrategy.PARAGRAPH.value == "PARAGRAPH"
    assert ChunkStrategy.SEMANTIC.value == "SEMANTIC"
    assert ChunkStrategy.RECURSIVE.value == "RECURSIVE"
    assert ChunkStrategy.CODE_AWARE.value == "CODE_AWARE"


def test_index_status_model():
    status = IndexStatus(
        total_documents=5,
        total_chunks=25,
        index_size_bytes=1024,
        embedding_model="local-hash",
        status_message="Index healthy"
    )
    assert status.total_documents == 5
    assert status.total_chunks == 25


def test_knowledge_manager_health_check():
    mgr = KnowledgeManager()
    mgr.initialize()
    hc = mgr.health_check()
    assert hc["available"] is True
    assert "metrics" in hc
    assert "index_status" in hc
    mgr.shutdown()


def test_ingest_document_tool_schema():
    tool = IngestDocumentTool()
    schema = tool.get_schema()
    assert schema["name"] == "ingest_document"
    assert "file_path" in schema["parameters"]["properties"]


def test_search_knowledge_tool_schema():
    tool = SearchKnowledgeTool()
    schema = tool.get_schema()
    assert schema["name"] == "search_knowledge"
    assert "query" in schema["parameters"]["properties"]


def test_summarize_document_tool_schema():
    tool = SummarizeDocumentTool()
    schema = tool.get_schema()
    assert schema["name"] == "summarize_document"


def test_list_documents_tool_schema():
    tool = ListDocumentsTool()
    schema = tool.get_schema()
    assert schema["name"] == "list_documents"


def test_remove_document_tool_schema():
    tool = RemoveDocumentTool()
    schema = tool.get_schema()
    assert schema["name"] == "remove_document"


def test_knowledge_manager_summarize_missing_document():
    mgr = KnowledgeManager()
    mgr.initialize()
    msg = mgr.summarize_document("unknown_doc_id_99")
    assert "not found" in msg.lower()
    mgr.shutdown()


def test_remove_document_tool_execution(tmp_path):
    tf = tmp_path / "remove_me.txt"
    tf.write_text("Text to be removed.", encoding="utf-8")

    tool_ingest = IngestDocumentTool()
    res_ingest = tool_ingest.execute(file_path=str(tf))
    doc_id = res_ingest.output["document_id"]

    tool_remove = RemoveDocumentTool(knowledge_manager=tool_ingest._manager)
    res_remove = tool_remove.execute(document_id=doc_id)
    assert res_remove.success is True
    assert res_remove.output["status"] == "removed"
