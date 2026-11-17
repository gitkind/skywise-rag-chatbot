# SkyWise evaluation and error analysis

Test set: `data/flywise_evaluation_dataset_v1.csv`, which has 20 questions.

| Type | IDs | What it tests |
|---|---|---|
| Answerable, single fact | Q01–Q10 | Factual lookups (refunds, pet size and weight, hotel during delays) |
| Answerable, multi-part | Q11–Q15 | Comparison and multi-part questions |
| Unanswerable | Q16–Q20 | Questions whose answer is **not** in the documents |

Ground truth for each answerable question is the document and PDF page(s) that hold the evidence (`GROUND_TRUTH` in `evaluate_retrieval.py`).

## 1. Retrieval (no API key needed)

`python evaluate_retrieval.py` reports Precision@5, Recall@5 and MRR on the 15 answerable questions.

### Default store (v2 chunks, collection `flywise_air_india_v1`)

| Method | Precision@5 | Recall@5 | MRR |
|---|---|---|---|
| Vector only (baseline) | 0.25 | 0.96 | 0.90 |
| **Hybrid (vector + BM25, RRF)** | **0.28** | **1.00** | **0.95** |
| Hybrid + cross-encoder re-rank (fused) | 0.28 | 1.00 | 0.90 |
| Hybrid + decomposition + re-rank | 0.28 | 1.00 | 0.90 |
| *Hybrid + old lexical re-rank (previous app)* | 0.28 | 1.00 | 0.87 |
| *Hybrid + cross-encoder only (not fused)* | — | 0.87 | 0.87 |

### Reproducible v3 chunks (`prepare_chunks.py`, collection `flywise_air_india_v3`)

| Method | Precision@5 | Recall@5 | MRR |
|---|---|---|---|
| Vector only | 0.27 | 0.98 | 0.86 |
| Hybrid | 0.27 | 0.93 | 0.90 |
| Hybrid + re-rank (fused) | 0.27 | 0.98 | 0.88 |

Full results are in `data/evaluation_results/` and `data/evaluation_results/v3_chunks/`.

### What the numbers say

* **Hybrid beats vector-only.** The clearest case is **Q11** ("cancellation + refund + assistance while waiting"). Vector-only found 1 of the 3 evidence pages (recall 0.33). Hybrid found all 3, because BM25 matched exact words like "refund" and "involuntary" on pages the embedding ranked lower.
* **Precision@5 is low by design.** Most questions have a single evidence page, so even a perfect retriever scores at most 1/5 = 0.2 on them.
* **A cross-encoder alone made retrieval worse.** It pushed Q01's evidence (CoC p.15) out of the top 5 in favour of pages that discuss cancellation more generally. Fusing the cross-encoder ranking with the hybrid ranking (Reciprocal Rank Fusion, k=10) fixed this. Recall stays at 1.00, and the fused version beats the app's previous keyword re-ranker (MRR 0.90 vs 0.87). It is used as the default re-ranker, and its 0-1 relevance score is shown on every source card.
* **The new v3 chunks are not better on this test set** (1 question different). The app keeps the v2 chunks as default. v3 is the documented, reproducible pipeline and is one environment variable away (see README).
* **Caveat:** with 15 questions, one question changes a metric by 0.07. These differences show direction, not statistical significance.

## 2. Answers (needs `OPENAI_API_KEY`)

`python evaluate_answers.py` runs the full guarded pipeline on all 20 questions. An LLM judge then scores:
* **correctness**, **faithfulness to the retrieved sources** and **relevance**, each on a 1–5 scale
* **refusal_ok**: answerable questions get answered, unanswerable ones get declined or answered "not established"
* invalid `[S#]` citation markers and latency

Results go to `data/evaluation_results/answer_evaluation*.csv`.

The earlier run of the unanswerable questions (`generation_abstention_results.csv`) handled all 5 correctly:

| ID | Question | Behaviour |
|---|---|---|
| Q16 | Free helicopter transfers? | Declined: not in the documents |
| Q17 | Exact cash compensation for every cancellation? | No universal amount is established |
| Q18 | Hand-baggage allowance in November 2026? | Only a 2015 document exists, so the answer is flagged as historical |
| Q19 | Can I bring a rabbit? | Eligibility not established; neither yes nor no |
| Q20 | Hotel guaranteed for every 2-hour delay? | No; it explains the conditions |

> That earlier run used prompt rules written for Q17 and Q19 specifically. Those rules are now replaced by general rules (see failure case 1). Re-run `evaluate_answers.py` to confirm the general rules still produce these results.

## 3. Failure cases and fixes

### Failure 1: prompt rules overfitted to the test questions
**Symptom:** `generation.py` had `if "rabbit" in q` and `if "every cancellation" in q` branches that injected special instructions. The bot passed Q17 and Q19, but a similar unseen question ("Can I bring a hamster?") got no such help.
**Fix (done):** removed the branches. Added general rules to the system prompt. Rule 12 says absence is not prohibition, so an unlisted category is "not established", never yes or no. Rule 13 says universal claims need explicit support.

### Failure 2: generic words let off-topic questions through the input guardrail
**Symptom:** "hooyian blorft policy" passed the input guardrail, because the word "policy" occurs in every document and counted as a keyword match. "Who won the cricket world cup?" also passed: its cosine similarity was 0.24, above the old 0.22 threshold.
**Fix (done):** generic domain words (policy, rules, flight...) no longer count. At least half of the question's specific words must occur in the corpus, otherwise semantic similarity must reach **0.30**. All 20 test questions score ≥ 0.47, so none is blocked.

### Failure 3: citations were never actually checked
**Symptom:** `verify_and_filter_citations` returned every retrieved chunk as a "source", whether or not the answer used it. The UI could show 5 sources for an answer built from 1.
**Fix (done):** the model now cites with `[S1]`, `[S2]`... markers. The output guardrail keeps only the sources the answer cites and flags markers that point at no source (hallucinated citations). Answers with no citations are labelled "No citations. Please verify".

### Failure 4: overlap was stored but never embedded
**Symptom:** in the v2 CSV the `overlap_context` column was metadata only. The overlapping words never appeared in the embedded text, so overlap gave no retrieval benefit.
**Fix (done):** `prepare_chunks.py` (v3) prepends the overlap to the chunk text before embedding.

### Failure 5: agent and partner documents were unreachable
**Symptom:** 93 of 238 chunks (General Booking, Schedule Change & IRROPS, ADM) were hard-filtered out, so questions about schedule-change rebooking got thin answers.
**Fix (done):** an "Include agent & partner policies" toggle in the UI (`audience_mode="all"`). When these sources are used, the prompt and the UI label them as agent-facing.

### Still open
* **Stale baggage data.** The only baggage source dates from 2015. The bot flags this, but it cannot give a current allowance. Fix: add the current airindia.com baggage page as a new document.
* **Small test set.** 20 questions are too few for confident comparisons. Fix: grow it to about 50, adding paraphrased and follow-up questions.
