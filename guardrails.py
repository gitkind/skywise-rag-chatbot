"""
FlyWise guardrails and re-ranking.

1. Input guardrail   - is the question related to anything in the corpus?
2. Re-ranking        - cross-encoder (ms-marco-MiniLM-L-6-v2) over the hybrid
                       candidates, with a lexical fallback if the model can't load.
3. Output guardrail  - the answer cites sources as [S1], [S2] ... ; only sources
                       the answer actually cites are shown, invalid markers are
                       flagged, and refusals are detected.
"""

from __future__ import annotations

import math
import re
from functools import lru_cache
from typing import Any

import config
from hybrid_retrieval import chunk_body, get_corpus, get_embedding_model, get_collection, is_passenger_facing

STOP_WORDS = set("""
a about above after again against all am an and any are as at be because been before being below
between both but by can cannot could did do does doing down during each few for from further had
has have having he her here hers him his how i if in into is it its itself just me more most my no
nor not of off on once only or other our ours out over own same she should so some such than that
the their them then there these they this those through to too under until up very was we were
what when where which while who whom why will with would you your yours get got air india flywise
skywise please tell know want need
""".split())


GENERIC_WORDS = {"policy", "policies", "rule", "rules", "airline", "flight", "flights",
                 "information", "details", "question", "help", "passenger", "passengers"}


def extract_content_tokens(text: str) -> list[str]:
    tokens = re.findall(r"\b[a-zA-Z0-9_\-]{2,}\b", text.lower())
    return [t for t in tokens if t not in STOP_WORDS]


# ------------------------------------------------------------------
# 1. Input guardrail
# ------------------------------------------------------------------

def assess_input_relevance(question: str) -> dict[str, Any]:
    """
    A question is out of scope when none of its content words occur in the
    corpus (BM25) AND its best cosine similarity to any chunk is below
    config.MIN_COSINE_SIMILARITY.
    """
    corpus = get_corpus()
    content_tokens = extract_content_tokens(question)

    matched, max_bm25 = [], 0.0
    for token in content_tokens:
        best = max(corpus["bm25"].get_scores([token]), default=0.0)
        if best > 0.5:
            matched.append(token)
        max_bm25 = max(max_bm25, best)

    max_cos = 0.0
    try:
        emb = get_embedding_model().encode(question, normalize_embeddings=True).tolist()
        res = get_collection().query(query_embeddings=[emb], n_results=3, include=["distances"])
        if res["distances"] and res["distances"][0]:
            max_cos = max(1.0 - d for d in res["distances"][0])
    except Exception:
        max_cos = 1.0  # never block on an infrastructure error

    has_content = bool(content_tokens)
    # Generic words ("policy", "rules") match every document, so they don't
    # count as evidence; at least half of the specific words must occur in the corpus.
    specific = [t for t in content_tokens if t not in GENERIC_WORDS]
    specific_matched = [t for t in matched if t not in GENERIC_WORDS]
    keyword_hit = bool(specific) and len(specific_matched) / len(specific) >= 0.5
    semantic_hit = max_cos >= config.MIN_COSINE_SIMILARITY
    is_relevant = (not has_content) or keyword_hit or semantic_hit

    return {
        "is_relevant": is_relevant,
        "content_tokens": content_tokens,
        "matched_content_tokens": matched,
        "max_content_bm25": float(max_bm25),
        "max_cos_sim": float(max_cos),
    }


# ------------------------------------------------------------------
# 2. Re-ranking
# ------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_cross_encoder():
    if not config.USE_CROSS_ENCODER:
        return None
    try:
        from sentence_transformers import CrossEncoder
        return CrossEncoder(config.RERANKER_MODEL, max_length=512)
    except Exception as exc:  # offline, no model, etc.
        print(f"[guardrails] cross-encoder unavailable, using lexical re-rank: {exc}")
        return None


def _lexical_score(question_tokens: set[str], chunk: dict) -> float:
    text = chunk_body(chunk.get("text", "")).lower()
    title = str(chunk["metadata"].get("document_title", "")).lower()
    density = (sum(t in text for t in question_tokens) / len(question_tokens)) if question_tokens else 0.0
    title_hits = sum(t in title for t in question_tokens)
    return chunk.get("rrf_score", 0.0) + 0.02 * density + 0.008 * title_hits


def rerank_chunks(question: str, chunks: list[dict], top_k: int = 5) -> list[dict]:
    """Re-score candidates; passenger-facing chunks get a small tie-breaking boost."""
    if not chunks:
        return []

    model = get_cross_encoder()
    scored = [dict(c) for c in chunks]  # input order = retriever (hybrid RRF) order

    if model is not None:
        # The cross-encoder alone dropped recall on our test set (it over-ranks
        # pages that merely mention the topic), so its ranking is fused with the
        # retriever's ranking using Reciprocal Rank Fusion (k=10) instead of
        # replacing it. See EVALUATION.md.
        logits = model.predict([(question, chunk_body(c["text"])) for c in scored], show_progress_bar=False)
        ce_order = sorted(range(len(scored)), key=lambda i: -float(logits[i]))
        ce_rank = {i: r for r, i in enumerate(ce_order, start=1)}
        for i, c in enumerate(scored):
            boost = 0.002 if is_passenger_facing(c["metadata"]) else 0.0
            c["relevance"] = 1.0 / (1.0 + math.exp(-float(logits[i])))  # sigmoid -> 0..1, for display
            c["rerank_score"] = 1.0 / (10 + i + 1) + 1.0 / (10 + ce_rank[i]) + boost
            c["rerank_method"] = "cross-encoder + RRF"
    else:
        tokens = set(extract_content_tokens(question))
        for c in scored:
            boost = 0.005 if is_passenger_facing(c["metadata"]) else 0.0
            c["rerank_score"] = _lexical_score(tokens, c) + boost
            c["relevance"] = None
            c["rerank_method"] = "lexical"

    scored.sort(key=lambda c: c["rerank_score"], reverse=True)
    return scored[:top_k]


# ------------------------------------------------------------------
# 3. Output guardrail
# ------------------------------------------------------------------

ABSTENTION_PATTERNS = [
    r"couldn'?t find enough information",
    r"could not find enough information",
    r"not established by the supplied",
    r"(do|does) not establish",
    r"no universal (compensation|amount)",
    r"not mentioned in the supplied",
    r"not (covered|addressed) (in|by) the supplied",
]
CITATION_RE = re.compile(r"\[S(\d{1,2})\]")


def is_abstention(answer: str) -> bool:
    return any(re.search(p, answer, re.IGNORECASE) for p in ABSTENTION_PATTERNS)


def format_page(meta: dict) -> str:
    start, end = meta.get("page_start", "?"), meta.get("page_end", "?")
    return f"p. {start}" if start == end else f"pp. {start}-{end}"


def verify_and_filter_citations(answer: str, chunks: list[dict]) -> tuple[list[dict], bool, list[int]]:
    """
    Returns (citations, is_abstention, invalid_markers).

    citations      - only the sources the answer cites with [S#] markers,
                     in the order they were first cited
    invalid_markers - [S#] numbers that point at no retrieved source
                     (a hallucinated citation)
    """
    abstained = is_abstention(answer)
    if not chunks:
        return [], True, []

    cited, invalid = [], []
    for match in CITATION_RE.finditer(answer):
        n = int(match.group(1))
        if 1 <= n <= len(chunks):
            if n not in cited:
                cited.append(n)
        elif n not in invalid:
            invalid.append(n)

    citations = []
    for n in cited:
        chunk = chunks[n - 1]
        meta = chunk.get("metadata", {})
        body = chunk_body(chunk.get("text", ""))
        citations.append({
            "marker": f"S{n}",
            "title": meta.get("document_title", "Air India policy document"),
            "pages": format_page(meta),
            "source_file": meta.get("source_file", ""),
            "effective_date": meta.get("effective_date", "Not stated"),
            "is_historical": bool(meta.get("is_historical"))
                              or "historical" in str(meta.get("effective_date", "")).lower(),
            "audience": meta.get("audience", ""),
            "excerpt": body[:320] + ("..." if len(body) > 320 else ""),
            "relevance": chunk.get("relevance"),
        })

    return citations, abstained, invalid
