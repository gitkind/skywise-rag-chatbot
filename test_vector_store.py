"""Quick smoke test for the FlyWise ChromaDB collection."""

import chromadb
from sentence_transformers import SentenceTransformer

import config

client = chromadb.PersistentClient(path=str(config.CHROMA_PATH))
collection = client.get_collection(config.COLLECTION_NAME)
model = SentenceTransformer(config.EMBEDDING_MODEL)

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
