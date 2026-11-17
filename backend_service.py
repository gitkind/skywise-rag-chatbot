"""
FlyWise backend: the full guarded RAG pipeline.

    question
      -> 0. plan (follow-up rewrite + query decomposition, only when needed)
      -> 1. input guardrail (is this about anything in the corpus?)
      -> 2. retrieval (hybrid vector+BM25 with RRF, per sub-question)
      -> 3. re-ranking (cross-encoder)
      -> 4. grounded generation (OpenAI, [S#] citations, streaming)
      -> 5. output guardrail (keep only cited sources, flag invalid citations,
            detect refusals)

The UI uses prepare() -> stream_answer() -> finalize() so it can stream text.
Scripts use get_flywise_response(), which runs all three.
"""

from __future__ import annotations

import time
from typing import Any, Iterator

import config
from guardrails import assess_input_relevance, rerank_chunks, verify_and_filter_citations
from hybrid_retrieval import hybrid_retrieve, vector_search
from query_decomposition import decomposed_retrieve, plan_query

FALLBACK_ANSWER = (
    "I couldn't find enough information in the supplied Air India policy "
    "documents to answer this confidently."
)

STRATEGIES = {
    "hybrid": "Hybrid (vector + BM25, RRF)",
    "vector": "Vector only (baseline)",
}

OUT_OF_SCOPE = (
    "I couldn't find enough information in the supplied Air India policy documents "
    "to answer this confidently.\n\nYour question doesn't match anything in the "
    "policies I have (Conditions of Carriage, pets in cabin, hand baggage, booking "
    "and schedule-change policies). Please check airindia.com or contact Air India."
)


def is_openai_configured() -> bool:
    return config.openai_configured()


def _step(trace: list, name: str, started: float, detail: str = "") -> float:
    now = time.perf_counter()
    trace.append({"step": name, "ms": round((now - started) * 1000), "detail": detail})
    return now


def prepare(question: str, *, top_k: int = 5, strategy: str = "hybrid",
            audience_mode: str = "passenger", decompose: bool = True,
            history: list[dict] | None = None) -> dict[str, Any]:
    """Steps 0-3. Returns everything needed to generate and display an answer."""
    question = (question or "").strip()
    trace: list[dict] = []
    t = time.perf_counter()

    # 0. Plan
    if decompose:
        plan = plan_query(question, history)
    else:
        plan = {"standalone": question, "sub_questions": [question], "method": "off"}
    standalone = plan["standalone"]
    detail = (f"{len(plan['sub_questions'])} sub-questions ({plan['method']})"
              if len(plan["sub_questions"]) > 1 else
              ("rewritten follow-up" if standalone != question else "single question"))
    t = _step(trace, "Plan query", t, detail)

    # 1. Input guardrail
    relevance = assess_input_relevance(standalone)
    t = _step(trace, "Input guardrail", t,
              f"max cosine {relevance['max_cos_sim']:.2f}, keyword hits {len(relevance['matched_content_tokens'])}")
    if not relevance["is_relevant"]:
        return {"question": question, "plan": plan, "relevance": relevance, "chunks": [],
                "blocked": True, "trace": trace, "strategy": strategy}

    # 2. Retrieve
    candidates_k = top_k * 3
    if strategy == "vector":
        candidates = vector_search(standalone, top_k=candidates_k, audience_mode=audience_mode)
    elif len(plan["sub_questions"]) > 1:
        candidates = decomposed_retrieve(plan["sub_questions"], top_k=candidates_k, audience_mode=audience_mode)
    else:
        candidates = hybrid_retrieve(standalone, top_k=candidates_k, audience_mode=audience_mode)
    t = _step(trace, "Retrieve", t, f"{len(candidates)} candidates, {STRATEGIES.get(strategy, strategy)}")

    # 3. Re-rank (per sub-question when decomposed, so every part keeps evidence)
    if len(plan["sub_questions"]) > 1 and strategy != "vector":
        per_q = max(3, -(-top_k // len(plan["sub_questions"])))  # ceil, at least 3 each
        chunks, seen = [], set()
        for sq in plan["sub_questions"]:
            pool = [c for c in candidates if sq in c.get("sub_questions", [])] or candidates
            for c in rerank_chunks(sq, pool, top_k=per_q):
                if c["chunk_id"] not in seen:
                    seen.add(c["chunk_id"])
                    chunks.append(c)
        chunks = chunks[: top_k + 2]
    else:
        chunks = rerank_chunks(standalone, candidates, top_k=top_k)
    method = chunks[0].get("rerank_method", "") if chunks else ""
    _step(trace, "Re-rank", t, f"top {len(chunks)} kept ({method})")

    return {"question": question, "plan": plan, "relevance": relevance, "chunks": chunks,
            "blocked": False, "trace": trace, "strategy": strategy}


def stream_answer(prepared: dict) -> Iterator[str]:
    """Step 4. Yields answer text. Falls back to a canned message when needed."""
    from generation import FALLBACK_ANSWER, stream_answer as llm_stream

    if prepared["blocked"]:
        yield OUT_OF_SCOPE
        return
    if not prepared["chunks"]:
        yield FALLBACK_ANSWER
        return
    if not is_openai_configured():
        yield ("**Offline mode:** `OPENAI_API_KEY` is not set, so no answer was generated. "
               f"Retrieval still ran. The {len(prepared['chunks'])} most relevant policy "
               "passages are listed under Sources.")
        return
    yield from llm_stream(prepared["plan"]["standalone"], prepared["chunks"], prepared["plan"]["sub_questions"])


def finalize(prepared: dict, answer: str, generation_ms: int | None = None) -> dict[str, Any]:
    """Step 5. Output guardrail and the final result payload."""
    trace = list(prepared["trace"])
    if generation_ms is not None:
        trace.append({"step": "Generate", "ms": generation_ms, "detail": config.LLM_MODEL})

    offline = not prepared["blocked"] and prepared["chunks"] and not is_openai_configured()
    if prepared["blocked"]:
        citations, abstained, invalid = [], True, []
    elif offline:
        # show every retrieved passage so retrieval can still be demonstrated
        fake = " ".join(f"[S{i}]" for i in range(1, len(prepared["chunks"]) + 1))
        citations, _, invalid = verify_and_filter_citations(fake, prepared["chunks"])
        abstained = False
    else:
        citations, abstained, invalid = verify_and_filter_citations(answer, prepared["chunks"])
        if answer.lstrip().startswith(FALLBACK_ANSWER[:40]):
            citations = []  # a refusal has no supporting sources to show

    if prepared["blocked"]:
        status = "out_of_scope"
    elif offline:
        status = "offline"
    elif abstained:
        status = "abstained"
    elif not citations:
        status = "uncited"
    else:
        status = "grounded"

    trace.append({"step": "Output guardrail", "ms": 0,
                  "detail": f"{len(citations)} cited, {len(invalid)} invalid markers"})

    return {
        "answer": answer,
        "citations": citations,
        "chunks": prepared["chunks"],
        "is_abstention": abstained,
        "status": status,
        "invalid_citations": invalid,
        "plan": prepared["plan"],
        "relevance": prepared["relevance"],
        "trace": trace,
        "evaluation": {
            "status": status,
            "max_cos_sim": round(prepared["relevance"]["max_cos_sim"], 4),
            "citations_verified": len(citations),
        },
    }


def get_flywise_response(question: str, top_k: int = 5, **options) -> dict[str, Any]:
    """Run the whole pipeline without streaming (for scripts and evaluation)."""
    if not (question or "").strip():
        return {"answer": "Please ask a question about Air India policies.", "citations": [], "chunks": [],
                "is_abstention": False, "status": "empty", "evaluation": {"status": "empty_query"}}
    prepared = prepare(question, top_k=top_k, **options)
    start = time.perf_counter()
    try:
        answer = "".join(stream_answer(prepared))
        error = None
    except Exception as exc:
        answer, error = f"Generation error: {exc}", str(exc)
    result = finalize(prepared, answer, round((time.perf_counter() - start) * 1000))
    result["error"] = error
    return result
