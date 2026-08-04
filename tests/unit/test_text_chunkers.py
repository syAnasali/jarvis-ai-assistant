"""Unit tests for ConfigurableTextChunker."""

import pytest
from app.knowledge.chunker import ConfigurableTextChunker
from app.knowledge.models import ChunkStrategy, Document, DocumentFormat


def test_paragraph_chunker():
    chunker = ConfigurableTextChunker(strategy=ChunkStrategy.PARAGRAPH)
    doc = Document(file_path="t.txt", format=DocumentFormat.TXT, title="t", raw_content="Para 1.\n\nPara 2.\n\nPara 3.")

    chunks = chunker.chunk(doc, chunk_size=100, overlap=10)
    assert len(chunks) >= 1
    assert "Para 1" in chunks[0].content


def test_code_aware_chunker():
    chunker = ConfigurableTextChunker(strategy=ChunkStrategy.CODE_AWARE)
    code = "def foo():\n    return 1\n\ndef bar():\n    return 2\n"
    doc = Document(file_path="s.py", format=DocumentFormat.CODE, title="s.py", raw_content=code)

    chunks = chunker.chunk(doc, chunk_size=100, overlap=10)
    assert len(chunks) >= 1
    assert "def foo()" in chunks[0].content
