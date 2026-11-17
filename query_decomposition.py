"""
Query Decomposition RAG.

1. plan_query()  - one LLM call that (a) rewrites a follow-up into a standalone
                   question using the chat history and (b) splits a multi-part
                   or comparison question into 1-4 self-contained sub-questions.
2. decomposed_retrieve() - runs hybrid retrieval for every sub-question and
                   merges the evidence with Reciprocal Rank Fusion, guaranteeing
                   each sub-question keeps its best chunks in the final context.

The LLM call is skipped for simple, single-part questions (needs_planning()),
so most questions pay no extra latency. Without an API key a rule-based
splitter is used instead.
"""

from __future__ import annotations

import json
import re

import config
from hybrid_retrieval import hybrid_retrieve, reciprocal_rank_fusion

MULTI_PART_HINTS = re.compile(
    r"\b(and|also|both|versus|vs\.?|compare|comparison|difference|differ|between|"
    r"as well as|plus|while)\b|\?.+\?",
    re.IGNORECASE,
)
FOLLOW_UP_HINTS = re.compile(r"^(and|what about|how about|also|then|that|it|this|those|they)\b|\b(it|that|this|them|those)\b",
                             re.IGNORECASE)

PLANNER_PROMPT = """
You prepare search queries for an Air India policy assistant.
Return JSON only: {"standalone": "...", "sub_questions": ["...", "..."]}

- "standalone": the user's latest question rewritten so it makes sense without
  the conversation (resolve words like "it", "that", "what about ...").
  If it is already standalone, copy it unchanged.
- "sub_questions": if the standalone question asks about several things, or
  compares things, split it into 2-4 short self-contained questions, one per
  fact needed. Otherwise return a list with just the standalone question.
Do not answer the question.
"""


def needs_planning(question: str, history: list[dict] | None) -> bool:
    if history and FOLLOW_UP_HINTS.search(question.strip()):
        return True
    return bool(MULTI_PART_HINTS.search(question)) and len(question.split()) >= 7


def rule_based_split(question: str) -> list[str]:
    parts = [p.strip(" ,.;") for p in re.split(r"\?\s+|\s*;\s*|,?\s+and also\s+", question) if p.strip(" ,.;")]
    parts = [p if p.endswith("?") else p + "?" for p in parts if len(p.split()) >= 3]
    return parts[:4] if len(parts) > 1 else [question]


def _history_text(history: list[dict] | None, turns: int = 3) -> str:
    if not history:
        return "(none)"
    recent = history[-turns * 2:]
    return "\n".join(f"{m['role']}: {m['content'][:400]}" for m in recent)


def plan_query(question: str, history: list[dict] | None = None) -> dict:
    """Returns {"standalone": str, "sub_questions": [str], "method": str}."""
    if not needs_planning(question, history):
        return {"standalone": question, "sub_questions": [question], "method": "none"}

    if not config.openai_configured():
        return {"standalone": question, "sub_questions": rule_based_split(question), "method": "rules"}

    try:
        from generation import get_client
        response = get_client().responses.create(
            model=config.LLM_MODEL,
            instructions=PLANNER_PROMPT,
            input=f"CONVERSATION SO FAR:\n{_history_text(history)}\n\nLATEST QUESTION:\n{question}",
        )
        raw = response.output_text.strip()
        raw = raw[raw.find("{"): raw.rfind("}") + 1]
        data = json.loads(raw)
        standalone = str(data.get("standalone") or question).strip()
        subs = [str(s).strip() for s in data.get("sub_questions", []) if str(s).strip()][:4]
        return {"standalone": standalone, "sub_questions": subs or [standalone], "method": "llm"}
    except Exception as exc:
        print(f"[query_decomposition] planner failed, using rules: {exc}")
        return {"standalone": question, "sub_questions": rule_based_split(question), "method": "rules"}


def decomposed_retrieve(sub_questions: list[str], top_k: int = 10, audience_mode: str = "passenger",
                        per_question_floor: int = 2) -> list[dict]:
    """Retrieve per sub-question, fuse with RRF, keep each sub-question's best chunks."""
    if len(sub_questions) <= 1:
        return hybrid_retrieve(sub_questions[0], top_k=top_k, audience_mode=audience_mode)

    per_question = [hybrid_retrieve(q, top_k=top_k, audience_mode=audience_mode) for q in sub_questions]
    by_id = {}
    for q, results in zip(sub_questions, per_question):
        for r in results:
            entry = by_id.setdefault(r["chunk_id"], dict(r, sub_questions=[]))
            entry["sub_questions"].append(q)

    must_keep = []
    for results in per_question:
        for r in results[:per_question_floor]:
            if r["chunk_id"] not in must_keep:
                must_keep.append(r["chunk_id"])

    fused = reciprocal_rank_fusion([[r["chunk_id"] for r in results] for results in per_question])
    ordered = must_keep + [cid for cid, _ in fused if cid not in must_keep]

    merged = []
    for cid in ordered[:max(top_k, len(must_keep))]:
        entry = by_id[cid]
        entry["rrf_score"] = dict(fused).get(cid, entry.get("rrf_score", 0.0))
        merged.append(entry)
    return merged


if __name__ == "__main__":
    q = input("Question: ")
    plan = plan_query(q)
    print(json.dumps(plan, indent=2))
    for r in decomposed_retrieve(plan["sub_questions"], top_k=6):
        print(r["metadata"].get("document_title"), r["metadata"].get("page_start"), r.get("sub_questions"))
