
from hybrid_retrieval import hybrid_retrieve
from generation import generate_answer


def ask_flywise(question):

    print("\nSearching Air India policy documents...")

    chunks = hybrid_retrieve(question, top_k=8)

    if not chunks:
        return (
            "I couldn't find enough information in the "
            "supplied Air India policy documents."
        )

    print(f"Retrieved {len(chunks)} policy chunks.")
    print("Generating grounded response...\n")

    answer = generate_answer(question, chunks)

    return answer


if __name__ == "__main__":

    print("=" * 60)
    print("       FLYWISE - HYBRID AIR INDIA ASSISTANT")
    print("=" * 60)

    while True:

        question = input("\nYou: ").strip()

        if question.lower() in ["exit", "quit", "bye"]:
            print("FlyWise: Goodbye!")
            break

        if not question:
            continue

        answer = ask_flywise(question)

        print("\nFlyWise:")
        print(answer)
        print("\n" + "-" * 60)
