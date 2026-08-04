"""Embedding providers for local VLM embeddings and deterministic offline vector generation."""

import math
import hashlib
from typing import List, Optional
import urllib.request
import json
from app.core.logger import JarvisLogger
from app.knowledge.interfaces import EmbeddingProvider

logger = JarvisLogger.get_logger("embedding_provider")


class LocalHashEmbeddingProvider(EmbeddingProvider):
    """Fast, deterministic 64-dimensional normalized vector generator for offline use & testing."""

    def __init__(self, vector_dim: int = 64) -> None:
        self.vector_dim = vector_dim

    def embed_text(self, text: str) -> List[float]:
        """Generates a deterministic 64-dimensional normalized vector using MD5/SHA256 hashing."""
        tokens = text.lower().split()
        vec = [0.0] * self.vector_dim

        for i, word in enumerate(tokens):
            h = hashlib.sha256(word.encode("utf-8")).digest()
            for j in range(min(len(h), self.vector_dim)):
                val = (h[j] - 128) / 128.0
                vec[j] += val

        # Cosine normalization
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        else:
            vec = [1.0 / math.sqrt(self.vector_dim)] * self.vector_dim

        return vec

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generates embeddings for a batch of text strings."""
        return [self.embed_text(t) for t in texts]


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Embedding provider connecting to local Ollama API server with fallback to LocalHash."""

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "nomic-embed-text",
        fallback_dim: int = 64
    ) -> None:
        self.host = host.rstrip("/")
        self.model = model
        self.fallback = LocalHashEmbeddingProvider(vector_dim=fallback_dim)

    def embed_text(self, text: str) -> List[float]:
        """Queries local Ollama embeddings endpoint."""
        url = f"{self.host}/api/embeddings"
        payload = {"model": self.model, "prompt": text}
        data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                if resp.status == 200:
                    res_json = json.loads(resp.read().decode("utf-8"))
                    emb = res_json.get("embedding")
                    if isinstance(emb, list) and len(emb) > 0:
                        return [float(x) for x in emb]
        except Exception as e:
            logger.warning(f"Ollama embeddings endpoint unavailable ({e}). Using LocalHash fallback.")

        return self.fallback.embed_text(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Batch embedding generation."""
        return [self.embed_text(t) for t in texts]
