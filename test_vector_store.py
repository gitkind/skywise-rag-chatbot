"""Quick smoke test for the FlyWise ChromaDB collection."""

from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent
client = chromadb.PersistentClient(path=str(ROOT / "vector_store"))
collection = client.get_collection("flywise_air_india_v1")
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

query = "What happens if my pet weighs more than 32 kg?"
query_vector = model.encode(
    [query], normalize_embeddings=True, convert_to_numpy=True
)[0].tolist()

results = collection.query(
    query_embeddings=[query_vector],
    n_results=5,
    include=["documents", "metadatas", "distances"]
)

for i, (doc, meta, distance) in enumerate(zip(
    results["documents"][0],
    results["metadatas"][0],
    results["distances"][0]
), start=1):
    print(f"\n--- Result {i} | cosine distance={distance:.4f} ---")
    print("Document:", meta.get("document_title"))
    print("Pages:", meta.get("page_start"), "-", meta.get("page_end"))
    print("Audience:", meta.get("audience"))
    print(doc[:700])
