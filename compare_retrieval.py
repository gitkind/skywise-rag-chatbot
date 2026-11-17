
from retrieval import retrieve_documents
from hybrid_retrieval import hybrid_retrieve


TEST_QUESTIONS = [
    "What happens if Air India cancels my flight? Am I eligible for a refund or an alternative flight?",
    "What are the requirements for carrying a pet in the cabin on an Air India flight, including the maximum weight and carrier dimensions?",
    "Does Air India provide free helicopter transfers for passengers?"
]


def display_results(method_name, results):
    print(f"\n{'=' * 70}")
    print(f"{method_name}")
    print("=" * 70)

    if not results:
        print("No results retrieved.")
        return

    for rank, result in enumerate(results[:5], start=1):
        metadata = result.get("metadata", {})

        source = metadata.get("document_title", "Unknown document")
        page = metadata.get("page_start", "Unknown")
        text = result.get("text", "")

        print(f"\nRank: {rank}")
        print(f"Source: {source}")
        print(f"Page: {page}")
        
        if result.get("distance") is not None:
            print(f"Vector distance: {result['distance']:.4f}")

        if result.get("rrf_score") is not None:
            print(f"RRF score: {result['rrf_score']:.5f}")

        print(f"Content: {text[:450]}...")
        print("-" * 70)


def main():
    print("\nFLYWISE - RETRIEVAL COMPARISON")
    print("Vector RAG vs Hybrid RAG")

    for number, question in enumerate(TEST_QUESTIONS, start=1):
        print("\n\n" + "#" * 70)
        print(f"TEST QUESTION {number}")
        print("#" * 70)
        print(question)

        print("\nRunning vector retrieval...")
        vector_results = retrieve_documents(question, top_k=8)

        print("Running hybrid retrieval...")
        hybrid_results = hybrid_retrieve(question, top_k=8)

        display_results("VECTOR-ONLY RETRIEVAL", vector_results)
        display_results("HYBRID RETRIEVAL", hybrid_results)

    print("\n\nCOMPARISON COMPLETED.")


if __name__ == "__main__":
    main()
