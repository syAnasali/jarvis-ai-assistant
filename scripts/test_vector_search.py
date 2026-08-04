"""Diagnostic script testing vector embedding generation and vector similarity search."""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, ".")

from app.knowledge.embeddings import LocalHashEmbeddingProvider
from app.knowledge.index import LocalVectorStore
from app.knowledge.models import DocumentChunk


def main() -> None:
    print("==================================================")
    print("Testing Vector Search Diagnostics")
    print("==================================================")

    provider = LocalHashEmbeddingProvider()
    store = LocalVectorStore()

    emb1 = provider.embed_text("Artificial Intelligence and Machine Learning Notes")
    emb2 = provider.embed_text("Operating Systems Kernel and Memory Architecture")

    c1 = DocumentChunk(document_id="doc1", content="AI and ML Notes", chunk_index=0, embedding=tuple(emb1))
    c2 = DocumentChunk(document_id="doc2", content="OS Kernel Notes", chunk_index=0, embedding=tuple(emb2))

    store.add_chunks([c1, c2])

    query_emb = provider.embed_text("Neural Networks and Deep Learning AI")
    matches = store.search(query_emb, top_k=2)

    print(f"Vector Search Matches: {len(matches)}")
    assert len(matches) == 2
    best_chunk, best_score = matches[0]
    print(f"Top Match: chunk_id={best_chunk.chunk_id}, score={best_score:.4f}")
    assert best_score > 0.0
    print("PASS: Vector search similarity scores verified.")

    print("\nALL VECTOR SEARCH DIAGNOSTICS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
