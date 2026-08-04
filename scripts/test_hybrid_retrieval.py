"""Diagnostic script testing hybrid vector similarity and BM25 keyword search."""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, ".")

from app.knowledge.embeddings import LocalHashEmbeddingProvider
from app.knowledge.index import LocalVectorStore
from app.knowledge.models import DocumentChunk, KnowledgeQuery
from app.knowledge.retriever import HybridRetrieverEngine


def main() -> None:
    print("==================================================")
    print("Testing Hybrid Retrieval Diagnostics")
    print("==================================================")

    provider = LocalHashEmbeddingProvider()
    store = LocalVectorStore()

    emb1 = provider.embed_text("Operating Systems Virtual Memory and Page Tables")
    c1 = DocumentChunk(document_id="doc_os", content="Operating Systems Virtual Memory and Page Tables", chunk_index=0, embedding=tuple(emb1))
    store.add_chunks([c1])

    retriever = HybridRetrieverEngine(vector_store=store, embedding_provider=provider)
    query = KnowledgeQuery(query_text="Virtual Memory Page Tables", top_k=1, alpha=0.7)

    results = retriever.retrieve(query)
    print(f"Hybrid Results: count={len(results)}")
    assert len(results) == 1
    res = results[0]
    print(f"Hybrid Match: combined_score={res.score:.4f}, sem={res.semantic_score:.4f}, kw={res.keyword_score:.4f}")
    assert res.score > 0.0
    print("PASS: Hybrid score fusion verified.")

    print("\nALL HYBRID RETRIEVAL DIAGNOSTICS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
