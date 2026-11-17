"""Central configuration for FlyWise. Override any value with an environment variable or .env."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

# Data and vector store (absolute paths so scripts work from any directory).
# Default: the v2 chunks (collection v1), which scored best in evaluation.
# The reproducible v3 chunks from prepare_chunks.py are one switch away:
#   FLYWISE_CHUNKS_CSV=data/flywise_air_india_chunks_v3.csv
#   FLYWISE_COLLECTION=flywise_air_india_v3
CHUNKS_CSV = ROOT / os.getenv("FLYWISE_CHUNKS_CSV", "data/flywise_air_india_chunks_v2.csv")
CHROMA_PATH = ROOT / "vector_store"
COLLECTION_NAME = os.getenv("FLYWISE_COLLECTION", "flywise_air_india_v1")

# Models
EMBEDDING_MODEL = os.getenv("FLYWISE_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
RERANKER_MODEL = os.getenv("FLYWISE_RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
USE_CROSS_ENCODER = os.getenv("FLYWISE_USE_CROSS_ENCODER", "1") == "1"
LLM_MODEL = os.getenv("FLYWISE_LLM_MODEL", "gpt-5.5")

# Retrieval
VECTOR_TOP_K = 20
BM25_TOP_K = 20
RRF_K = 60

# Input guardrail thresholds (tuned on data/flywise_evaluation_dataset_v1.csv)
# In-scope test questions score >= 0.47; off-topic ones ("capital of France",
# "cricket world cup") score 0.10-0.24.
MIN_COSINE_SIMILARITY = float(os.getenv("FLYWISE_MIN_COSINE", "0.30"))
MIN_KEYWORD_BM25 = 1.0


def openai_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))
