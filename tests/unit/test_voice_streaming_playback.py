"""Unit tests for sentence-level token streaming chunker."""

import pytest
from app.voice.pipeline import chunk_sentences


def test_chunk_sentences_splits_by_sentence_delimiters():
    tokens = ["Hello ", "world. ", "This ", "is ", "a ", "test! ", "How ", "are ", "you?"]
    sentences = list(chunk_sentences(tokens))
    assert len(sentences) == 3
    assert sentences[0] == "Hello world."
    assert sentences[1] == "This is a test!"
    assert sentences[2] == "How are you?"


def test_chunk_sentences_handles_newlines():
    tokens = ["First line.\nSecond line.\nThird line."]
    sentences = list(chunk_sentences(tokens))
    assert len(sentences) == 3
    assert "First line." in sentences[0]
    assert "Second line." in sentences[1]
    assert "Third line." in sentences[2]


def test_chunk_sentences_trailing_remainder():
    tokens = ["Incomplete sentence"]
    sentences = list(chunk_sentences(tokens))
    assert len(sentences) == 1
    assert sentences[0] == "Incomplete sentence"
