"""
End-to-end answer evaluation (assignment section 6).

Runs the full guarded pipeline on all 20 questions in
data/flywise_evaluation_dataset_v1.csv and scores every answer with an
LLM judge on:

  correctness   1-5  matches the expected evidence / behaviour
  faithfulness  1-5  every claim is supported by the retrieved sources
  relevance     1-5  answers the question that was asked
  refusal_ok    bool answerable -> answered; unanswerable -> abstained
                     (or said "not established") instead of inventing

Also records: citation count, invalid [S#] markers, latency.

Run (needs OPENAI_API_KEY):
  python evaluate_answers.py
Output:
  data/evaluation_results/answer_evaluation.csv
  data/evaluation_results/answer_evaluation_summary.csv
"""

from __future__ import annotations

import json
import time

import pandas as pd

import config
from backend_service import get_flywise_response
from generation import build_context, get_client

DATASET = config.ROOT / "data" / "flywise_evaluation_dataset_v1.csv"
OUT_DIR = config.ROOT / "data" / "evaluation_results"

JUDGE_PROMPT = """
You grade answers from an Air India policy chatbot. Return JSON only:
{"correctness": 1-5, "faithfulness": 1-5, "relevance": 1-5, "refusal_ok": true|false, "reason": "one sentence"}

correctness  - does the answer match the EXPECTED EVIDENCE and EXPECTED BEHAVIOUR?
faithfulness - is every factual claim supported by the RETRIEVED SOURCES? (5 = fully)
relevance    - does it answer the question asked, without padding?
refusal_ok   - for an "unanswerable" question: true if the bot declined, or said the
               documents do not establish the answer, without inventing facts.
               For an answerable question: true if the bot gave a substantive answer.
"""


def judge(row: pd.Series, result: dict) -> dict:
    prompt = (
        f"QUESTION TYPE: {row['question_type']}\n"
        f"QUESTION: {row['question']}\n"
        f"EXPECTED EVIDENCE: {row['expected_evidence']}\n"
        f"EXPECTED BEHAVIOUR: {row['expected_behavior']}\n\n"
        f"RETRIEVED SOURCES:\n{build_context(result['chunks']) or '(none)'}\n\n"
        f"CHATBOT ANSWER:\n{result['answer']}"
    )
    response = get_client().responses.create(model=config.LLM_MODEL, instructions=JUDGE_PROMPT, input=prompt)
    raw = response.output_text
    return json.loads(raw[raw.find("{"): raw.rfind("}") + 1])


def main():
    if not config.openai_configured():
        raise SystemExit("OPENAI_API_KEY is not set (add it to .env).")

    df = pd.read_csv(DATASET)
    rows = []
    for _, row in df.iterrows():
        print(f"[{row['question_id']}] {row['question']}")
        start = time.perf_counter()
        result = get_flywise_response(row["question"])
        latency = time.perf_counter() - start
        try:
            scores = judge(row, result)
        except Exception as exc:
            scores = {"reason": f"judge error: {exc}"}
        rows.append({
            "question_id": row["question_id"],
            "question_type": row["question_type"],
            "question": row["question"],
            "status": result["status"],
            "citations": len(result["citations"]),
            "invalid_citations": len(result.get("invalid_citations", [])),
            "latency_s": round(latency, 2),
            **scores,
            "answer": result["answer"],
            "sources": "; ".join(f"{c['marker']} {c['title']} {c['pages']}" for c in result["citations"]),
        })
        print(f"    -> {result['status']}, {scores}")

    out = pd.DataFrame(rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_DIR / "answer_evaluation.csv", index=False, encoding="utf-8-sig")

    out["group"] = out["question_type"].map(lambda t: "unanswerable" if t == "unanswerable" else "answerable")
    summary = out.groupby("group").agg(
        questions=("question_id", "count"),
        correctness=("correctness", "mean"),
        faithfulness=("faithfulness", "mean"),
        relevance=("relevance", "mean"),
        refusal_ok_rate=("refusal_ok", "mean"),
        invalid_citations=("invalid_citations", "sum"),
        avg_latency_s=("latency_s", "mean"),
    ).round(2)
    summary.to_csv(OUT_DIR / "answer_evaluation_summary.csv")
    print("\n", summary.to_string())


if __name__ == "__main__":
    main()
