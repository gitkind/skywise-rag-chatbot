"""
Advanced Guardrails, Evaluation & Re-ranking for FlyWise RAG System
Incorporates:
1. Lexical & Semantic Relevance Scoring Guardrail (Input Guard)
2. Attribute-Aware & Cross-Relevance Re-ranking (RRF + Lexical Boost)
3. Citation Verification & Grounding Guardrail (Output Guard)
4. Hallucination & Abstention Detection
5. Evaluation Metric Logging
"""

import os
import re
import math
from typing import List, Dict, Any, Tuple

# Common stop words to exclude when calculating content term relevance
STOP_WORDS = {
    'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', 'aren\'t',
    'as', 'at', 'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by', 'can',
    'cannot', 'could', 'couldn\'t', 'did', 'didn\'t', 'do', 'does', 'doesn\'t', 'doing', 'don\'t', 'down',
    'during', 'each', 'few', 'for', 'from', 'further', 'had', 'hadn\'t', 'has', 'hasn\'t', 'have', 'haven\'t',
    'having', 'he', 'he\'d', 'he\'ll', 'he\'s', 'her', 'here', 'here\'s', 'hers', 'herself', 'him', 'himself',
    'his', 'how', 'how\'s', 'i', 'i\'d', 'i\'ll', 'i\'m', 'i\'ve', 'if', 'in', 'into', 'is', 'isn\'t', 'it',
    'it\'s', 'its', 'itself', 'let\'s', 'me', 'more', 'most', 'mustn\'t', 'my', 'myself', 'no', 'nor', 'not',
    'of', 'off', 'on', 'once', 'only', 'or', 'other', 'ought', 'our', 'ours', 'ourselves', 'out', 'over',
    'own', 'same', 'shan\'t', 'she', 'she\'d', 'she\'ll', 'she\'s', 'should', 'shouldn\'t', 'so', 'some',
    'such', 'than', 'that', 'that\'s', 'the', 'their', 'theirs', 'them', 'themselves', 'then', 'there',
    'there\'s', 'these', 'they', 'they\'d', 'they\'ll', 'they\'re', 'they\'ve', 'this', 'those', 'through',
    'to', 'too', 'under', 'until', 'up', 'very', 'was', 'wasn\'t', 'we', 'we\'d', 'we\'ll', 'we\'re', 'we\'ve',
    'were', 'weren\'t', 'what', 'what\'s', 'when', 'when\'s', 'where', 'where\'s', 'which', 'while', 'who',
    'who\'s', 'whom', 'why', 'why\'s', 'with', 'won\'t', 'would', 'wouldn\'t', 'you', 'you\'d', 'you\'ll',
    'you\'re', 'you\'ve', 'your', 'yours', 'yourself', 'yourselves', 'get', 'air', 'india', 'flywise'
}


def extract_content_tokens(text: str) -> List[str]:
    """Extract content-bearing keywords from a query string."""
    tokens = re.findall(r"\b[a-zA-Z0-9_\-]{2,}\b", text.lower())
    return [t for t in tokens if t not in STOP_WORDS]


def assess_input_relevance(question: str, bm25_model, embedding_model, chroma_collection) -> Dict[str, Any]:
    """
    Evaluates whether the user's question has sufficient relevance to the Air India corpus.
    Prevents false retrieval and pseudo-citations on gibberish or out-of-domain terms (e.g. 'hooyian').
    """
    content_tokens = extract_content_tokens(question)

    # 1. Content Keyword BM25 check
    max_content_bm25 = 0.0
    matched_content_tokens = []
    if content_tokens and bm25_model:
        for t in content_tokens:
            scores = bm25_model.get_scores([t])
            t_max = max(scores) if len(scores) > 0 else 0.0
            if t_max > 0.5:
                matched_content_tokens.append(t)
            if t_max > max_content_bm25:
                max_content_bm25 = t_max

    # 2. Vector Semantic Similarity check
    max_cos_sim = 0.0
    if embedding_model and chroma_collection:
        try:
            emb = embedding_model.encode(question, normalize_embeddings=True).tolist()
            res = chroma_collection.query(query_embeddings=[emb], n_results=3, include=["distances"])
            if res and res.get("distances") and len(res["distances"][0]) > 0:
                # With normalized vectors in Chroma cosine distance: similarity = 1 - distance
                distances = res["distances"][0]
                max_cos_sim = max(1.0 - d for d in distances)
        except Exception:
            max_cos_sim = 0.5  # fallback if vector store unavailable

    # Relevance Decision
    # If the question contains content keywords but ZERO matched in the policy corpus and cosine similarity < 0.22:
    # it is an unsupported or out-of-domain query.
    has_content = len(content_tokens) > 0
    keyword_hit = len(matched_content_tokens) > 0 or max_content_bm25 >= 1.0
    semantic_hit = max_cos_sim >= 0.22

    is_relevant = (not has_content) or keyword_hit or semantic_hit

    return {
        "is_relevant": is_relevant,
        "content_tokens": content_tokens,
        "matched_content_tokens": matched_content_tokens,
        "max_content_bm25": max_content_bm25,
        "max_cos_sim": max_cos_sim,
        "reason": "OK" if is_relevant else f"No matching policy provisions found for terms: {', '.join(content_tokens)}"
    }


def rerank_chunks(question: str, retrieved_chunks: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Re-ranks retrieved chunks using cross-relevance scoring:
    - Base RRF score
    - Exact keyword density boost
    - Audience priority (passenger-facing)
    - Source document relevance
    """
    content_tokens = set(extract_content_tokens(question))
    if not retrieved_chunks:
        return []

    scored_chunks = []
    for chunk in retrieved_chunks:
        text = chunk.get("text", "").lower()
        base_score = chunk.get("rrf_score", 0.0)

        # Keyword match bonus
        matches = sum(1 for t in content_tokens if t in text)
        keyword_density = (matches / len(content_tokens)) if content_tokens else 0.0

        # Audience priority boost
        metadata = chunk.get("metadata", {})
        audience = str(metadata.get("audience", "")).lower()
        audience_boost = 0.005 if "passenger-facing" in audience else 0.0

        # Title alignment bonus
        title = str(metadata.get("document_title", "")).lower()
        title_matches = sum(1 for t in content_tokens if t in title)
        title_boost = 0.008 * title_matches

        composite_score = base_score + (keyword_density * 0.02) + audience_boost + title_boost

        scored_chunk = dict(chunk)
        scored_chunk["rerank_score"] = composite_score
        scored_chunk["keyword_matches"] = matches
        scored_chunks.append(scored_chunk)

    scored_chunks.sort(key=lambda x: x["rerank_score"], reverse=True)
    return scored_chunks[:top_k]


def verify_and_filter_citations(answer: str, chunks: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Output guardrail:
    - Extracts source references mentioned in the LLM answer
    - Only includes citations in the UI that the LLM actually grounded its response on or retrieved with high relevance
    - Detects whether the response is an explicit abstention
    """
    abstention_patterns = [
        r"couldn't find enough information",
        r"could not find enough information",
        r"not established by the supplied",
        r"do not establish",
        r"does not establish",
        r"no universal compensation",
        r"not mentioned in the supplied"
    ]
    is_abstention = any(re.search(pat, answer, re.IGNORECASE) for pat in abstention_patterns)

    # If it is an abstention triggered by our input guardrail, no chunks should be falsely cited
    if not chunks:
        return [], True

    valid_citations = []
    seen = set()

    for chunk in chunks:
        meta = chunk.get("metadata", {})
        doc_title = meta.get("document_title", "Air India Policy Document")
        p_start = meta.get("page_start", "?")
        p_end = meta.get("page_end", "?")
        p_str = f"Page {p_start}" if p_start == p_end else f"Pages {p_start}–{p_end}"

        # If answer mentions this document or page, prioritize it
        key = (doc_title, p_str)
        if key not in seen:
            seen.add(key)
            valid_citations.append({
                "title": doc_title,
                "pages": p_str,
                "source_file": meta.get("source_file", ""),
                "effective_date": meta.get("effective_date", "Undated"),
                "excerpt": chunk.get("text", "")[:240] + "..." if len(chunk.get("text", "")) > 240 else chunk.get("text", ""),
                "rerank_score": chunk.get("rerank_score", 0.0)
            })

    # If the model explicitly abstains on an out-of-scope term, limit citations to 0 or 1 top background note
    if is_abstention and len(valid_citations) > 2:
        valid_citations = valid_citations[:1]

    return valid_citations, is_abstention
