# FlyWise Phase 4 — Embeddings and ChromaDB

## Folder setup

```text
FlyWise/
├── data/
│   └── flywise_air_india_chunks_v2.csv
├── vector_store/
├── build_vector_store.py
├── test_vector_store.py
└── requirements.txt
```

Copy the supplied `flywise_air_india_chunks_v2.csv` into `data/`.

## Install

```bash
python -m venv .venv
# Windows:
.venv\\Scripts\\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

## Build the vector store

```bash
python build_vector_store.py
```

The first run downloads `sentence-transformers/all-MiniLM-L6-v2`.
It creates a persistent ChromaDB database in `vector_store/`.

## Smoke test

```bash
python test_vector_store.py
```

## Design choices

- Model: `all-MiniLM-L6-v2` (384-dimensional sentence embeddings).
- Similarity: cosine distance.
- Batch size: 64 CSV records per indexing batch.
- IDs: stable `chunk_id` values from the chunk CSV.
- Metadata: source document, topic, audience, effective date and PDF page range.
- Rebuild behavior: the script recreates the named collection on each run to avoid stale chunks.

The index contains all audiences, including agent-facing records. The application retrieval layer should filter to passenger-facing material for ordinary passenger questions, and only expose agent-facing material in an explicitly selected agent-support mode.
