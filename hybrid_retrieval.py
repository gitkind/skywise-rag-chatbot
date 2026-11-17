"""
FlyWise retrieval layer: vector search, BM25 keyword search and their
Reciprocal Rank Fusion (Hybrid RAG).

Models and indexes load lazily on first use and are cached for the process,
so importing this module is cheap (important for Streamlit reruns).

Audience modes
  "passenger" (default): only passenger-facing documents (Conditions of
                Carriage, Pets, Hand Baggage).
  "all":        every document, including the agent / travel-partner
                policies (General Booking, Schedule Change & IRROPS, ADM).
                Passenger-facing chunks still get a small boost in re-ranking.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from functools import lru_cache

import config

AUDIENCE_MODES = ("passenger", "all")


# ------------------------------------------------------------------
# Lazy resources
# ------------------------------------------------------------------

def tokenize(text: str) -> list[str]:
    return re.findall(r"\b\w+\b", text.lower())


@lru_cache(maxsize=1)
def get_embedding_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(config.EMBEDDING_MODEL)


@lru_cache(maxsize=1)
def get_collection():
    import chromadb
    client = chromadb.PersistentClient(path=str(config.CHROMA_PATH))
    try:
        return client.get_collection(name=config.COLLECTION_NAME)
    except Exception as exc:  # collection missing
        raise RuntimeError(
            f"Vector store collection '{config.COLLECTION_NAME}' not found in "
            f"{config.CHROMA_PATH}. Run `python build_vector_store.py` first."
        ) from exc


@lru_cache(maxsize=1)
def get_corpus():
    """All chunks plus a BM25 index over them."""
    from rank_bm25 import BM25Okapi

    data = get_collection().get(include=["documents", "metadatas"])
    documents, metadatas, ids = data["documents"], data["metadatas"], data["ids"]
    bm25 = BM25Okapi([tokenize(d) for d in documents])
    id_to_index = {doc_id: i for i, doc_id in enumerate(ids)}
    return {
        "documents": documents,
        "metadatas": metadatas,
        "ids": ids,
        "bm25": bm25,
        "id_to_index": id_to_index,
    }


def warm_up() -> dict:
    """Load everything once (used by the UI on startup)."""
    corpus = get_corpus()
    get_embedding_model()
    return {"chunks": len(corpus["ids"]),
            "documents": len({m.get("document_title") for m in corpus["metadatas"]})}


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def is_passenger_facing(metadata: dict) -> bool:
    return "passenger-facing" in str(metadata.get("audience", "")).lower()


def allowed(metadata: dict, audience_mode: str) -> bool:
    return audience_mode == "all" or is_passenger_facing(metadata)


def chunk_body(text: str) -> str:
    """Chunk text without the metadata header (used for display and re-ranking)."""
    parts = re.split(r"\r?\n\r?\n", text, maxsplit=1)
    return parts[1].strip() if len(parts) == 2 else text.strip()


def _make_result(index: int, **scores) -> dict:
    corpus = get_corpus()
    return {
        "chunk_id": corpus["ids"][index],
        "text": corpus["documents"][index],
        "metadata": corpus["metadatas"][index],
        **scores,
    }


# ------------------------------------------------------------------
# Retrievers
# ------------------------------------------------------------------

def vector_search(question: str, top_k: int = config.VECTOR_TOP_K,
                  audience_mode: str = "all") -> list[dict]:
    corpus = get_corpus()
    embedding = get_embedding_model().encode(question, normalize_embeddings=True).tolist()
    where = None if audience_mode == "all" else {"audience": "Passenger-facing"}
    res = get_collection().query(
        query_embeddings=[embedding],
        n_results=min(top_k, len(corpus["ids"])),
        where=where,
        include=["distances"],
    )
    return [
        _make_result(corpus["id_to_index"][cid], distance=dist, similarity=1 - dist)
        for cid, dist in zip(res["ids"][0], res["distances"][0])
    ]


def bm25_search(question: str, top_k: int = config.BM25_TOP_K,
                audience_mode: str = "all") -> list[dict]:
    corpus = get_corpus()
    scores = corpus["bm25"].get_scores(tokenize(question))
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    results = []
    for i in order:
        if scores[i] <= 0:
            break
        if allowed(corpus["metadatas"][i], audience_mode):
            results.append(_make_result(i, bm25_score=float(scores[i])))
        if len(results) >= top_k:
            break
    return results


def reciprocal_rank_fusion(rankings: list[list[str]], k: int = config.RRF_K) -> list[tuple[str, float]]:
    """score(d) = sum over rankings of 1 / (k + rank(d))."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)


def deduplicate(results: list[dict], threshold: float = 0.90) -> list[dict]:
    """Drop near-duplicate chunks from the same source page."""
    kept, seen = [], []
    for r in results:
        meta = r["metadata"]
        norm = " ".join(chunk_body(r["text"]).lower().split())
        key = (meta.get("source_file"), meta.get("page_start"))
        if any(k == key and SequenceMatcher(None, norm, t).ratio() >= threshold for k, t in seen):
            continue
        seen.append((key, norm))
        kept.append(r)
    return kept


def hybrid_retrieve(question: str, top_k: int = 8, audience_mode: str = "passenger") -> list[dict]:
    """Vector + BM25 candidates merged with Reciprocal Rank Fusion."""
    if audience_mode not in AUDIENCE_MODES:
        raise ValueError(f"audience_mode must be one of {AUDIENCE_MODES}")

    vector_hits = vector_search(question, config.VECTOR_TOP_K, audience_mode)
    keyword_hits = bm25_search(question, config.BM25_TOP_K, audience_mode)

    similarity = {h["chunk_id"]: h["similarity"] for h in vector_hits}
    bm25_scores = {h["chunk_id"]: h["bm25_score"] for h in keyword_hits}
    fused = reciprocal_rank_fusion([
        [h["chunk_id"] for h in vector_hits],
        [h["chunk_id"] for h in keyword_hits],
    ])

    corpus = get_corpus()
    candidates = [
        _make_result(
            corpus["id_to_index"][cid],
            rrf_score=score,
            similarity=similarity.get(cid),
            bm25_score=bm25_scores.get(cid),
            distance=None,
        )
        for cid, score in fused
    ]
    return deduplicate(candidates)[:top_k]


if __name__ == "__main__":
    while True:
        q = input("\nAsk an Air India policy question (exit to quit): ").strip()
        if q.lower() in {"exit", "quit"}:
            break
        for i, r in enumerate(hybrid_retrieve(q), start=1):
            m = r["metadata"]
            print(f"\n[{i}] RRF {r['rrf_score']:.4f} | {m.get('document_title')} p.{m.get('page_start')}")
            print(chunk_body(r["text"])[:300])
