"""Built-in Knowledge Base tools for document ingestion, search, summarization, listing, and removal."""

from typing import Any, Dict, Optional
from app.knowledge.manager import KnowledgeManager
from app.tools.base import BaseTool
from app.tools.models import ToolPermission, ToolResult


class IngestDocumentTool(BaseTool):
    """Tool to ingest a local file or directory path into the Knowledge Base."""

    name = "ingest_document"
    description = "Parses, chunks, embeds, and indexes a local file or directory path into the RAG Knowledge Base."
    permission_level = ToolPermission.SAFE

    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to local file or directory to ingest."
            }
        },
        "required": ["file_path"]
    }

    def __init__(self, knowledge_manager: Optional[KnowledgeManager] = None) -> None:
        self._manager = knowledge_manager or KnowledgeManager()

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "permission_level": self.permission_level.value,
            "parameters": self.parameters
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        file_path = kwargs.get("file_path", "")
        if not file_path:
            return ToolResult(tool_name=self.name, success=False, output={}, error="file_path must not be empty.")

        try:
            doc = self._manager.ingest_document(file_path)
            return ToolResult(
                tool_name=self.name,
                success=True,
                output={
                    "document_id": doc.document_id,
                    "title": doc.title,
                    "format": doc.format.value,
                    "char_count": doc.char_count,
                    "file_path": doc.file_path
                }
            )
        except Exception as e:
            return ToolResult(tool_name=self.name, success=False, output={}, error=f"Ingest document tool failed: {e}")


class SearchKnowledgeTool(BaseTool):
    """Tool to perform hybrid vector and keyword search across the RAG Knowledge Base."""

    name = "search_knowledge"
    description = "Searches indexed Knowledge Base documents returning ranked matches and structured citations."
    permission_level = ToolPermission.SAFE

    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query text."
            },
            "top_k": {
                "type": "integer",
                "description": "Maximum number of results to return.",
                "default": 5
            }
        },
        "required": ["query"]
    }

    def __init__(self, knowledge_manager: Optional[KnowledgeManager] = None) -> None:
        self._manager = knowledge_manager or KnowledgeManager()

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "permission_level": self.permission_level.value,
            "parameters": self.parameters
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        query = kwargs.get("query", "")
        top_k = kwargs.get("top_k", 5)

        if not query:
            return ToolResult(tool_name=self.name, success=False, output={}, error="query must not be empty.")

        try:
            results, citations = self._manager.query_knowledge(query_text=query, top_k=top_k)
            rendered_citations = self._manager.citation_formatter.render_markdown_citations(citations)

            matches_summary = [
                {
                    "citation_id": cit.citation_id,
                    "title": cit.document_title,
                    "file_url": cit.file_url,
                    "snippet": cit.snippet
                }
                for cit in citations
            ]

            return ToolResult(
                tool_name=self.name,
                success=True,
                output={
                    "total_matches": len(results),
                    "matches": matches_summary,
                    "rendered_markdown": rendered_citations
                }
            )
        except Exception as e:
            return ToolResult(tool_name=self.name, success=False, output={}, error=f"Search knowledge tool failed: {e}")


class SummarizeDocumentTool(BaseTool):
    """Tool to summarize a stored Knowledge Base document."""

    name = "summarize_document"
    description = "Generates a summary of an ingested document in the Knowledge Base."
    permission_level = ToolPermission.SAFE

    parameters = {
        "type": "object",
        "properties": {
            "document_id": {
                "type": "string",
                "description": "Document ID or file path name."
            }
        },
        "required": ["document_id"]
    }

    def __init__(self, knowledge_manager: Optional[KnowledgeManager] = None) -> None:
        self._manager = knowledge_manager or KnowledgeManager()

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "permission_level": self.permission_level.value,
            "parameters": self.parameters
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        doc_id = kwargs.get("document_id", "")
        if not doc_id:
            return ToolResult(tool_name=self.name, success=False, output={}, error="document_id must not be empty.")

        try:
            summary = self._manager.summarize_document(doc_id)
            return ToolResult(
                tool_name=self.name,
                success=True,
                output={
                    "document_id": doc_id,
                    "summary": summary
                }
            )
        except Exception as e:
            return ToolResult(tool_name=self.name, success=False, output={}, error=f"Summarize document tool failed: {e}")


class ListDocumentsTool(BaseTool):
    """Tool to list all indexed documents in the Knowledge Base."""

    name = "list_documents"
    description = "Lists all indexed documents and metadata stored in the RAG Knowledge Base."
    permission_level = ToolPermission.SAFE

    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }

    def __init__(self, knowledge_manager: Optional[KnowledgeManager] = None) -> None:
        self._manager = knowledge_manager or KnowledgeManager()

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "permission_level": self.permission_level.value,
            "parameters": self.parameters
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            docs = self._manager.list_documents()
            summary = [
                {
                    "document_id": d.document_id,
                    "title": d.title,
                    "format": d.format.value,
                    "file_size_bytes": d.file_size_bytes,
                    "char_count": d.char_count
                }
                for d in docs
            ]
            return ToolResult(
                tool_name=self.name,
                success=True,
                output={
                    "total_documents": len(docs),
                    "documents": summary
                }
            )
        except Exception as e:
            return ToolResult(tool_name=self.name, success=False, output={}, error=f"List documents tool failed: {e}")


class RemoveDocumentTool(BaseTool):
    """Tool to remove a document and its embeddings from the Knowledge Base."""

    name = "remove_document"
    description = "Deletes an ingested document and its vector embeddings from the Knowledge Base."
    permission_level = ToolPermission.SAFE

    parameters = {
        "type": "object",
        "properties": {
            "document_id": {
                "type": "string",
                "description": "Unique document_id to remove."
            }
        },
        "required": ["document_id"]
    }

    def __init__(self, knowledge_manager: Optional[KnowledgeManager] = None) -> None:
        self._manager = knowledge_manager or KnowledgeManager()

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "permission_level": self.permission_level.value,
            "parameters": self.parameters
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        doc_id = kwargs.get("document_id", "")
        if not doc_id:
            return ToolResult(tool_name=self.name, success=False, output={}, error="document_id must not be empty.")

        try:
            self._manager.remove_document(doc_id)
            return ToolResult(
                tool_name=self.name,
                success=True,
                output={
                    "document_id": doc_id,
                    "status": "removed"
                }
            )
        except Exception as e:
            return ToolResult(tool_name=self.name, success=False, output={}, error=f"Remove document tool failed: {e}")
