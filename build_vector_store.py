"""
FlyWise Phase 4: Generate embeddings and persist them in ChromaDB.

Input:
  data/flywise_air_india_chunks_v2.csv   (default; or the v3 CSV from prepare_chunks.py)

Output:
  vector_store/  (persistent ChromaDB database)

Run:
  python build_vector_store.py
  python build_vector_store.py --csv data/flywise_air_india_chunks_v3.csv --collection flywise_air_india_v3
"""

import argparse
from pathlib import Path
import math
import pandas as pd
from sentence_transformers import SentenceTransformer
import chromadb

import config

ROOT = config.ROOT
DB_PATH = config.CHROMA_PATH
MODEL_NAME = config.EMBEDDING_MODEL
BATCH_SIZE = 64

REQUIRED_COLUMNS = [
    "chunk_id", "document_title", "source_file", "topic", "audience",
    "effective_date", "page_start", "page_end", "source_page_reference", "text"
]


def clean_metadata_value(value):
    """Chroma metadata supports strings, integers, floats and booleans."""
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
        return value
    return str(value)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, default=config.CHUNKS_CSV)
    parser.add_argument("--collection", default=config.COLLECTION_NAME)
    args = parser.parse_args()
    CSV_PATH = args.csv if args.csv.is_absolute() else ROOT / args.csv
    COLLECTION_NAME = args.collection

    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"Could not find {CSV_PATH}. Run `python prepare_chunks.py` first."
        )

    df = pd.read_csv(CSV_PATH)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"CSV is missing required columns: {missing}")

    df = df.dropna(subset=["chunk_id", "text"]).copy()
    df["chunk_id"] = df["chunk_id"].astype(str)
    df["text"] = df["text"].astype(str).str.strip()
    df = df[df["text"] != ""]

    if df["chunk_id"].duplicated().any():
        duplicates = df.loc[df["chunk_id"].duplicated(), "chunk_id"].tolist()
        raise ValueError(f"Duplicate chunk IDs found: {duplicates[:10]}")

    print(f"Loaded {len(df)} valid chunks.")
    print(f"Loading embedding model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    client = chromadb.PersistentClient(path=str(DB_PATH))
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

    # Rebuild the collection deterministically so rerunning the script does
    # not leave stale records from an earlier dataset version.
    existing = collection.count()
    if existing:
        print(f"Removing {existing} existing records from {COLLECTION_NAME}.")
        client.delete_collection(COLLECTION_NAME)
        collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )

    for start in range(0, len(df), BATCH_SIZE):
        batch = df.iloc[start:start + BATCH_SIZE]
        documents = batch["text"].tolist()

        vectors = model.encode(
            documents,
            batch_size=32,
            show_progress_bar=False,
            normalize_embeddings=True,
            convert_to_numpy=True
        )

        metadatas = []
        for _, row in batch.iterrows():
            metadata = {}
            for col in [
                "document_title", "source_file", "topic", "audience",
                "effective_date", "page_start", "page_end",
                "source_page_reference", "word_count", "estimated_tokens",
                "is_historical"
            ]:
                if col in row.index:
                    value = clean_metadata_value(row[col])
                    if value is not None:
                        metadata[col] = value
            if "is_historical" not in metadata:
                metadata["is_historical"] = "historical" in str(
                    metadata.get("effective_date", "")).lower()
            metadata["is_historical"] = bool(metadata["is_historical"])
            metadata["airline"] = "Air India"
            metadatas.append(metadata)

        collection.add(
            ids=batch["chunk_id"].tolist(),
            documents=documents,
            embeddings=vectors.tolist(),
            metadatas=metadatas
        )
        print(f"Embedded {min(start + len(batch), len(df))}/{len(df)} chunks")

    print("\nVector store created successfully.")
    print(f"Database path: {DB_PATH}")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Stored records: {collection.count()}")
    print(f"Embedding model: {MODEL_NAME}")
    print("Embedding dimension:", model.get_sentence_embedding_dimension())


if __name__ == "__main__":
    main()
