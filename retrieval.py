"""
Baseline (vector-only) retrieval, kept for comparison with Hybrid RAG.
Shares the cached model and collection with hybrid_retrieval.py.
"""

from hybrid_retrieval import vector_search


def retrieve_documents(question, top_k=8, audience_mode="all"):
    """Top-k chunks by cosine similarity. Baseline: no audience filter by default."""
    return vector_search(question, top_k=top_k, audience_mode=audience_mode)


if __name__ == "__main__":
    question = input("\nAsk an Air India policy question: ")
    for index, chunk in enumerate(retrieve_documents(question), start=1):
        metadata = chunk["metadata"]
        print(f"\nResult {index} | distance {chunk['distance']:.4f}")
        print(f"Document: {metadata.get('document_title')} | Pages: "
              f"{metadata.get('page_start')}-{metadata.get('page_end')}")
        print(chunk["text"][:500])
