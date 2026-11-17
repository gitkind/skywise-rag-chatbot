# SkyWise: Air India policy assistant (RAG chatbot)

A Retrieval-Augmented Generation chatbot that answers Air India passengers' questions from six **official Air India policy PDFs**. It cites the exact PDF page for every claim, and it says so when the documents don't contain the answer.

**Live app:** https://skywise-air-india.streamlit.app

**Industry:** Travel & Hospitality · **Company:** Air India · **Users:** passengers asking about cancellations, refunds, delays, pets in the cabin and baggage.

## Pipeline

```
PDFs ─▶ chunking ─▶ embeddings ─▶ ChromaDB ─▶ retrieval ─▶ re-rank ─▶ LLM ─▶ cited answer
         prepare_     MiniLM-L6     cosine      hybrid       cross-     gpt-5.5   [S1] [S2]
         chunks.py    (384-dim)                 vector+BM25  encoder    grounded  + output
                                                (RRF)        + RRF      prompt    guardrail
      ▲ input guardrail: refuse questions that match nothing in the corpus
      ▲ query decomposition: split multi-part questions, rewrite follow-ups
```

| Stage | File | Choice and why |
|---|---|---|
| Data | `pdfs/` | 6 public Air India PDFs: Conditions of Carriage, Pets in Cabin, Hand Baggage (2015, flagged historical), General Booking (Mar 2026), Schedule Change & IRROPS (May 2025), ADM/GDS policy. |
| Chunking | `prepare_chunks.py` | Page-bounded, sentence-packed to ~110 words (max 160), 25-word overlap embedded into the text, metadata header (document, audience, effective date, page). Small chunks keep one policy clause together. Page bounds make exact citations possible. Empty pages and exact duplicates are removed. |
| Embeddings | `build_vector_store.py` | `all-MiniLM-L6-v2`, normalized, cosine. Free, local and fast. That is enough for about 250 chunks. |
| Vector store | `vector_store/` | ChromaDB, stored on disk. |
| Retrieval | `hybrid_retrieval.py` | **Hybrid RAG:** vector top 20 + BM25 top 20, merged with Reciprocal Rank Fusion (k=60). Near-duplicates from the same page are dropped. The audience filter defaults to passenger documents, and agent policies can be included. |
| Query decomposition | `query_decomposition.py` | **Query-decomposition RAG:** multi-part or comparison questions are split into sub-questions. Each is retrieved separately, then the results are merged with RRF. Follow-ups are rewritten using chat history. This only runs when the question needs it. |
| Re-ranking | `guardrails.py` | Cross-encoder `ms-marco-MiniLM-L-6-v2`, fused with the hybrid ranking. On its own it hurt recall (see EVALUATION.md). |
| Generation | `generation.py` | OpenAI Responses API with streaming. A 15-rule grounding prompt: cite `[S#]`, keep conditions, "absence ≠ prohibition", no universal claims without support, flag historical and agent-facing sources. |
| Guardrails | `guardrails.py` | Input: refuses off-topic questions before calling the LLM. Output: shows only the sources the answer cites, flags invalid `[S#]` markers and detects refusals. |
| Orchestration | `backend_service.py` | `prepare()`, then `stream_answer()`, then `finalize()`, plus a per-step timing trace. |
| UI | `app.py`, `ui_theme.py` | Streamlit chat with streamed answers, source chips and passage cards, a "How this answer was made" trace, retrieval settings and feedback buttons. |

## Run it

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file (see `.env.example`):

```
OPENAI_API_KEY=sk-...
```

Without a key the app still runs in **offline mode**. Retrieval, re-ranking and sources all work, but no answer is generated.

```bash
streamlit run app.py
```

The first start downloads the embedding and re-ranker models (about 180 MB).

### Rebuild the data (optional)

```bash
python prepare_chunks.py                 # PDFs -> data/flywise_air_india_chunks_v3.csv
python build_vector_store.py             # default v2 chunks -> collection flywise_air_india_v1
python build_vector_store.py --csv data/flywise_air_india_chunks_v3.csv --collection flywise_air_india_v3
```

To use the v3 chunks in the app, set `FLYWISE_CHUNKS_CSV=data/flywise_air_india_chunks_v3.csv` and `FLYWISE_COLLECTION=flywise_air_india_v3` in `.env`. All settings are in `config.py`.

## Evaluate

```bash
python evaluate_retrieval.py   # Precision@5 / Recall@5 / MRR, 4 retrieval methods (no API key)
python evaluate_answers.py     # correctness, faithfulness, relevance, refusals with an LLM judge (needs key)
python verify_test_queries.py  # quick 5-question smoke test
python compare_retrieval.py    # vector vs hybrid, side by side
```

Results and the failure analysis are in **[EVALUATION.md](EVALUATION.md)**. Headline: hybrid retrieval reaches **Recall@5 = 1.00, MRR = 0.95**, against 0.96 and 0.90 for vector-only. In the earlier answer run, all 5 unanswerable test questions were declined correctly. Re-run `evaluate_answers.py` to confirm this with the new prompt.

## Project layout

```
app.py, ui_theme.py          Streamlit UI
backend_service.py           guarded RAG pipeline
config.py                    paths, models, thresholds (env-overridable)
prepare_chunks.py            PDF -> chunks
build_vector_store.py        chunks -> ChromaDB
hybrid_retrieval.py          vector, BM25, RRF
retrieval.py                 vector-only baseline
query_decomposition.py       sub-questions + follow-up rewriting
guardrails.py                input guardrail, re-ranker, citation checks
generation.py                prompt + OpenAI calls
evaluate_*.py                evaluation scripts
data/                        chunks, test set, results
```

*Academic project. Always confirm critical travel details on airindia.com.*
