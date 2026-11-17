
import re
import chromadb

from difflib import SequenceMatcher
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer


# ==========================================
# 1. CONFIGURATION
# ==========================================

CHROMA_PATH = "vector_store"
COLLECTION_NAME = "flywise_air_india_v1"

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

VECTOR_TOP_K = 20
BM25_TOP_K = 20
RRF_K = 60


# ==========================================
# 2. LOAD MODELS AND DATABASE
# ==========================================

print("Loading embedding model...")
embedding_model = SentenceTransformer(EMBEDDING_MODEL)

print("Connecting to ChromaDB...")
client = chromadb.PersistentClient(path=CHROMA_PATH)

collection = client.get_collection(
    name=COLLECTION_NAME
)

print("Loading policy corpus...")

corpus = collection.get(
    include=["documents", "metadatas"]
)

documents = corpus["documents"]
metadatas = corpus["metadatas"]
document_ids = corpus["ids"]


# ==========================================
# 3. BM25 INDEX
# ==========================================

def tokenize(text):
    """Basic tokenization for BM25."""
    return re.findall(r"\b\w+\b", text.lower())


print("Building BM25 index...")

tokenized_corpus = [
    tokenize(document) for document in documents
]

bm25 = BM25Okapi(tokenized_corpus)


# ==========================================
# 4. RECIPROCAL RANK FUSION
# ==========================================

def reciprocal_rank_fusion(rankings, k=RRF_K):
    """Merge ranked lists using Reciprocal Rank Fusion."""

    scores = {}

    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking, start=1):

            scores[chunk_id] = (
                scores.get(chunk_id, 0)
                + 1 / (k + rank)
            )

    return sorted(
        scores.items(),
        key=lambda item: item[1],
        reverse=True
    )


# ==========================================
# 5. HYBRID RETRIEVAL
# ==========================================

def hybrid_retrieve(question, top_k=8):

    # Vector retrieval
    query_embedding = embedding_model.encode(
        question,
        normalize_embeddings=True
    ).tolist()

    vector_results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(VECTOR_TOP_K, len(documents)),
        include=["documents", "metadatas", "distances"]
    )

    vector_ids = vector_results["ids"][0]

    # BM25 retrieval
    tokenized_query = tokenize(question)

    bm25_scores = bm25.get_scores(tokenized_query)

    bm25_indices = sorted(
        range(len(bm25_scores)),
        key=lambda i: bm25_scores[i],
        reverse=True
    )[:BM25_TOP_K]

    bm25_ids = [
        document_ids[i] for i in bm25_indices
    ]

    # Reciprocal Rank Fusion
    fused_results = reciprocal_rank_fusion(
        [vector_ids, bm25_ids]
    )

    # Map document IDs to corpus indices
    id_to_index = {
        doc_id: i
        for i, doc_id in enumerate(document_ids)
    }

    final_results = []
    seen_chunks = []

    # Audience filtering and duplicate suppression
    for chunk_id, score in fused_results:

        index = id_to_index[chunk_id]

        metadata = metadatas[index]
        text = documents[index]

        audience = str(
            metadata.get("audience", "")
        ).lower()

        # Keep passenger-facing documents by default
        if "passenger-facing" not in audience:
            continue

        normalized_text = " ".join(
            text.lower().split()
        )

        # Check for near-duplicates from the same source/page
        is_duplicate = False

        for previous in seen_chunks:

            same_source = (
                metadata.get("source_file")
                == previous["source"]
            )

            same_page = (
                metadata.get("page_start")
                == previous["page"]
            )

            if same_source and same_page:

                similarity = SequenceMatcher(
                    None,
                    normalized_text,
                    previous["text"]
                ).ratio()

                if similarity >= 0.90:
                    is_duplicate = True
                    break

        if is_duplicate:
            continue

        seen_chunks.append({
            "source": metadata.get("source_file"),
            "page": metadata.get("page_start"),
            "text": normalized_text
        })

        final_results.append({
            "text": text,
            "metadata": metadata,
            "distance": None,
            "rrf_score": score
        })

        if len(final_results) >= top_k:
            break

    return final_results


# ==========================================
# 6. TEST HYBRID RETRIEVAL
# ==========================================

if __name__ == "__main__":

    while True:

        question = input(
            "\nAsk an Air India policy question (exit to quit): "
        ).strip()

        if question.lower() in ["exit", "quit"]:
            break

        if not question:
            continue

        results = hybrid_retrieve(question)

        print("\nHYBRID RETRIEVAL RESULTS")
        print("=" * 60)

        for i, result in enumerate(results, start=1):

            metadata = result["metadata"]

            print(f"\nResult {i}")
            print(f"RRF Score: {result['rrf_score']:.5f}")
            print(f"Document: {metadata.get('document_title')}")
            print(f"Audience: {metadata.get('audience')}")
            print(f"Effective Date: {metadata.get('effective_date')}")
            print(f"Source: {metadata.get('source_file')}")

            print(
                f"Pages: {metadata.get('page_start')} - "
                f"{metadata.get('page_end')}"
            )

            print(f"Text: {result['text']}")
