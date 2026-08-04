"""Unit tests for Embedding Providers."""

import pytest
from app.knowledge.embeddings import LocalHashEmbeddingProvider, OllamaEmbeddingProvider


def test_local_hash_embedding_provider():
    provider = LocalHashEmbeddingProvider(vector_dim=64)
    emb = provider.embed_text("Artificial Intelligence and Machine Learning")
    assert len(emb) == 64
    assert isinstance(emb[0], float)


def test_ollama_embedding_provider_fallback():
    provider = OllamaEmbeddingProvider(host="http://localhost:99999", fallback_dim=64)
    emb = provider.embed_text("Test fallback behavior")
    assert len(emb) == 64
