"""Configurable Text Chunker supporting Paragraph, Semantic, Recursive, and Code-Aware chunking."""

import re
from typing import List, Optional, Tuple
from app.core.logger import JarvisLogger
from app.knowledge.interfaces import TextChunker
from app.knowledge.models import ChunkStrategy, Document, DocumentChunk, DocumentFormat

logger = JarvisLogger.get_logger("text_chunker")


class ConfigurableTextChunker(TextChunker):
    """Configurable text chunker with multi-strategy support."""

    def __init__(self, strategy: ChunkStrategy = ChunkStrategy.RECURSIVE) -> None:
        self.strategy = strategy

    def chunk(self, document: Document, chunk_size: int = 512, overlap: int = 64) -> List[DocumentChunk]:
        """Splits document text into DocumentChunk instances based on chosen strategy."""
        logger.info(f"Chunking document '{document.title}' using strategy '{self.strategy.value}' (size={chunk_size}, overlap={overlap})...")

        if document.format == DocumentFormat.CODE or self.strategy == ChunkStrategy.CODE_AWARE:
            raw_chunks = self._chunk_code_aware(document.raw_content, chunk_size, overlap)
        elif self.strategy == ChunkStrategy.PARAGRAPH:
            raw_chunks = self._chunk_paragraph(document.raw_content, chunk_size, overlap)
        elif self.strategy == ChunkStrategy.SEMANTIC:
            raw_chunks = self._chunk_semantic(document.raw_content, chunk_size, overlap)
        else:
            raw_chunks = self._chunk_recursive(document.raw_content, chunk_size, overlap)

        chunks: List[DocumentChunk] = []
        current_line = 1

        for idx, (chunk_text, start_line, end_line) in enumerate(raw_chunks):
            chunk = DocumentChunk(
                document_id=document.document_id,
                content=chunk_text,
                chunk_index=idx,
                start_line=start_line,
                end_line=end_line,
                metadata={
                    "file_path": document.file_path,
                    "format": document.format.value,
                    "strategy": self.strategy.value
                }
            )
            chunks.append(chunk)

        logger.info(f"Generated {len(chunks)} chunks for document '{document.title}'.")
        return chunks

    def _chunk_paragraph(self, text: str, size: int, overlap: int) -> List[Tuple[str, int, int]]:
        """Paragraph-based chunking."""
        paragraphs = text.split("\n\n")
        return self._pack_segments(paragraphs, size, overlap)

    def _chunk_recursive(self, text: str, size: int, overlap: int) -> List[Tuple[str, int, int]]:
        """Recursive delimiter-based chunking."""
        delimiters = ["\n\n", "\n", ". ", " "]
        segments = [text]

        for d in delimiters:
            new_segments = []
            for seg in segments:
                if len(seg) > size:
                    sub = seg.split(d)
                    new_segments.extend(sub)
                else:
                    new_segments.append(seg)
            segments = new_segments

        return self._pack_segments(segments, size, overlap)

    def _chunk_semantic(self, text: str, size: int, overlap: int) -> List[Tuple[str, int, int]]:
        """Sentence-aware semantic chunking."""
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return self._pack_segments(sentences, size, overlap)

    def _chunk_code_aware(self, text: str, size: int, overlap: int) -> List[Tuple[str, int, int]]:
        """Code-aware block chunking (functions, classes)."""
        lines = text.splitlines()
        blocks: List[str] = []
        curr_block: List[str] = []

        for line in lines:
            if re.match(r"^\s*(def |class |function |public |private |interface )", line) and curr_block:
                blocks.append("\n".join(curr_block))
                curr_block = [line]
            else:
                curr_block.append(line)

        if curr_block:
            blocks.append("\n".join(curr_block))

        return self._pack_segments(blocks, size, overlap)

    def _pack_segments(self, segments: List[str], max_size: int, overlap: int) -> List[Tuple[str, int, int]]:
        """Packs segments into target size chunks while preserving line numbers."""
        results: List[Tuple[str, int, int]] = []
        curr_text = ""
        curr_start_line = 1
        line_counter = 1

        for seg in segments:
            seg_str = seg.strip()
            if not seg_str:
                continue

            seg_lines = seg_str.count("\n") + 1

            if len(curr_text) + len(seg_str) <= max_size:
                if curr_text:
                    curr_text += "\n\n" + seg_str
                else:
                    curr_text = seg_str
                    curr_start_line = line_counter
            else:
                if curr_text:
                    end_l = curr_start_line + curr_text.count("\n")
                    results.append((curr_text, curr_start_line, end_l))
                curr_text = seg_str
                curr_start_line = line_counter

            line_counter += seg_lines

        if curr_text:
            end_l = curr_start_line + curr_text.count("\n")
            results.append((curr_text, curr_start_line, end_l))

        return results if results else [(text[:max_size], 1, 1)]
