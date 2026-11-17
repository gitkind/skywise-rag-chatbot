"""
FlyWise grounded answer generation (OpenAI Responses API).

The prompt contains only general grounding rules. Earlier versions had
if-statements for specific test questions ("rabbit", "every cancellation");
those were replaced by general rules 12-15 below so behaviour generalises to
unseen questions instead of being tuned to the evaluation set.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Iterator

import config
from guardrails import format_page
from hybrid_retrieval import chunk_body

FALLBACK_ANSWER = (
    "I couldn't find enough information in the supplied Air India policy "
    "documents to answer this confidently."
)

SYSTEM_PROMPT = f"""
You are SkyWise, a customer-support assistant for Air India passengers.
Answer ONLY from the numbered policy sources supplied with each question.

CITATIONS
1. Cite every factual policy claim with the source marker(s) it comes from,
   written exactly like [S1] or [S2][S4], placed at the end of the sentence.
2. Only cite markers that appear in the supplied sources. Never invent a source.

GROUNDING
3. Never invent policies, fees, deadlines, procedures, benefits, compensation
   amounts or eligibility rules.
4. Keep the conditions, exceptions and qualifications that apply to a rule.
5. Distinguish airline-initiated cancellation from passenger-requested
   cancellation, and cancellation from delay.
6. Do not combine unrelated provisions just because they were retrieved together.
7. If sources conflict, say so and cite both. Never silently pick one.
8. If a source is marked historical or undated, say that the information may
   be out of date and should be confirmed with Air India.
9. Sources marked as agent-facing or travel-partner-facing describe rules for
   travel agents; say so when you use them for a passenger question.

SCOPE AND PRECISION
10. Answer the exact question first, in one or two sentences, then add detail.
11. If the sources do not answer the question, reply with:
    "{FALLBACK_ANSWER}"
    then say briefly what information is missing. Do not speculate.
12. Absence is not prohibition. If a policy lists eligible items or categories
    and the user asks about one that is not listed, say its eligibility is
    "not established by the supplied documents"; do not answer yes or no, do
    not call it prohibited, and suggest confirming with Air India.
13. Universal claims need explicit support. If the user asks whether one
    amount, guarantee or entitlement applies to every case, and the sources
    only describe conditional or case-specific provisions, say that no
    universal amount or guarantee is established, and summarise the
    conditions in one sentence instead of listing every conditional figure.
14. Never answer yes or no when the sources do not establish the answer.
15. Do not treat an old document as current policy.

STYLE
- Short paragraphs or bullet points, 80-220 words.
- Plain language a passenger understands. No preamble like "Based on the context".
"""


@lru_cache(maxsize=1)
def get_client():
    from openai import OpenAI
    return OpenAI()


def build_context(chunks: list[dict]) -> str:
    parts = []
    for n, chunk in enumerate(chunks, start=1):
        meta = chunk["metadata"]
        flags = []
        if "historical" in str(meta.get("effective_date", "")).lower() or meta.get("is_historical"):
            flags.append("HISTORICAL DOCUMENT")
        if "passenger-facing" not in str(meta.get("audience", "")).lower():
            flags.append(f"AUDIENCE: {meta.get('audience')}")
        flag_line = f"Flags: {', '.join(flags)}\n" if flags else ""
        parts.append(
            f"[S{n}] {meta.get('document_title', 'Unknown document')} "
            f"({format_page(meta)}), effective date: {meta.get('effective_date', 'not stated')}\n"
            f"{flag_line}{chunk_body(chunk['text'])}"
        )
    return "\n\n---\n\n".join(parts)


def build_user_prompt(question: str, chunks: list[dict], sub_questions: list[str] | None = None) -> str:
    sub = ""
    if sub_questions and len(sub_questions) > 1:
        sub = "The question has these parts; answer each one:\n" + "\n".join(
            f"- {q}" for q in sub_questions) + "\n\n"
    return (
        f"PASSENGER QUESTION:\n{question}\n\n{sub}"
        f"POLICY SOURCES:\n{build_context(chunks)}\n\n"
        "Answer using only these sources and cite them with [S#] markers."
    )


def generate_answer(question: str, retrieved_chunks: list[dict],
                    sub_questions: list[str] | None = None) -> str:
    response = get_client().responses.create(
        model=config.LLM_MODEL,
        instructions=SYSTEM_PROMPT,
        input=build_user_prompt(question, retrieved_chunks, sub_questions),
    )
    return response.output_text


def stream_answer(question: str, retrieved_chunks: list[dict],
                  sub_questions: list[str] | None = None) -> Iterator[str]:
    """Yields text deltas as the model writes them."""
    stream = get_client().responses.create(
        model=config.LLM_MODEL,
        instructions=SYSTEM_PROMPT,
        input=build_user_prompt(question, retrieved_chunks, sub_questions),
        stream=True,
    )
    for event in stream:
        if getattr(event, "type", "") == "response.output_text.delta":
            yield event.delta


if __name__ == "__main__":
    print("FlyWise generation module loaded. Model:", config.LLM_MODEL)
