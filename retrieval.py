
import chromadb
from sentence_transformers import SentenceTransformer

# Configuration
CHROMA_PATH = "vector_store"
COLLECTION_NAME = "flywise_air_india_v1"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Load embedding model
print("Loading embedding model...")
embedding_model = SentenceTransformer(EMBEDDING_MODEL)

# Connect to existing ChromaDB
print("Connecting to ChromaDB...")
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

collection = chroma_client.get_collection(
    name=COLLECTION_NAME
)


def retrieve_documents(question, top_k=8):
    """
    Retrieve the most relevant policy chunks for a user question.
    """

    query_embedding = embedding_model.encode(
        question,
        normalize_embeddings=True
    ).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )

    retrieved_chunks = []

    for i in range(len(results["documents"][0])):
        chunk = {
            "text": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i]
        }

        retrieved_chunks.append(chunk)

    return retrieved_chunks


if __name__ == "__main__":

    question = input("\nAsk an Air India policy question: ")

    chunks = retrieve_documents(question)

    print("\nRETRIEVED POLICY CHUNKS")
    print("=" * 60)

    for index, chunk in enumerate(chunks, start=1):
        metadata = chunk["metadata"]

        print(f"\nResult {index}")
        print(f"Distance: {chunk['distance']:.4f}")
        print(f"Document: {metadata.get('document_title')}")
        print(f"Pages: {metadata.get('page_start')} - {metadata.get('page_end')}")
        print(f"Text: {chunk['text']}")
