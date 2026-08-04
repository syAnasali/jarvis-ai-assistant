"""Structured Citation Formatter producing document attribution and clickable file scheme URLs."""

import os
from pathlib import Path
from typing import List
from app.core.logger import JarvisLogger
from app.knowledge.interfaces import CitationFormatter
from app.knowledge.models import Citation, RetrievalResult

logger = JarvisLogger.get_logger("citation_formatter")


class StructuredCitationFormatter(CitationFormatter):
    """Formats structured citations with clickable file:/// URLs."""

    def format_citations(self, results: List[RetrievalResult]) -> List[Citation]:
        """Formats structured citations from candidate retrieval results."""
        citations: List[Citation] = []

        for idx, res in enumerate(results):
            chunk = res.chunk
            doc = res.source_document

            file_path = doc.file_path if doc else chunk.metadata.get("file_path", "document")
            title = doc.title if doc else Path(file_path).name

            # Format Windows path as file:/// URL scheme
            clean_path = file_path.replace("\\", "/")
            if not clean_path.startswith("/"):
                clean_path = f"/{clean_path}"
            file_url = f"file://{clean_path}"

            snippet = chunk.content[:150].replace("\n", " ") + "..."

            cit = Citation(
                citation_id=f"cit_{idx + 1}",
                document_title=title,
                file_path=file_path,
                file_url=file_url,
                page_number=chunk.page_number,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                snippet=snippet
            )
            citations.append(cit)

        return citations

    def render_markdown_citations(self, citations: List[Citation]) -> str:
        """Renders formatted Markdown citation list with clickable file links."""
        lines: List[str] = ["### Sources & Citations:"]
        for cit in citations:
            loc = []
            if cit.page_number is not None:
                loc.append(f"Page {cit.page_number}")
            if cit.start_line is not None:
                loc.append(f"Line {cit.start_line}")

            loc_str = f" ({', '.join(loc)})" if loc else ""
            lines.append(f"- **[{cit.document_title}]({cit.file_url})**{loc_str}\n  *{cit.snippet}*")

        return "\n\n".join(lines)
