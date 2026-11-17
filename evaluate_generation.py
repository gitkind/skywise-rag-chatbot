
import pandas as pd
from pathlib import Path

from hybrid_retrieval import hybrid_retrieve
from generation import generate_answer


# Project paths
DATASET_PATH = Path("data/flywise_evaluation_dataset_v1.csv")
OUTPUT_DIR = Path("data/evaluation_results")
OUTPUT_PATH = OUTPUT_DIR / "generation_abstention_results.csv"

# Questions that should test abstention
TARGET_IDS = ["Q16", "Q17", "Q18", "Q19", "Q20"]

TOP_K = 8


def main():
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Evaluation dataset not found: {DATASET_PATH}"
        )

    df = pd.read_csv(DATASET_PATH)
    test_df = df[df["question_id"].isin(TARGET_IDS)].copy()

    if test_df.empty:
        raise ValueError("No matching questions found in the dataset.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    results = []

    print("=" * 65)
    print("FLYWISE - GENERATION AND ABSTENTION EVALUATION")
    print("=" * 65)

    for _, row in test_df.iterrows():
        question_id = row["question_id"]
        question = row["question"]

        print(f"\n[{question_id}] {question}")
        print("-" * 65)

        try:
            # Retrieve relevant policy chunks
            chunks = hybrid_retrieve(question, top_k=TOP_K)

            if not chunks:
                answer = (
                    "I couldn't find enough information in the "
                    "supplied Air India policy documents."
                )
                retrieved_sources = "No chunks retrieved"
            else:
                # Generate an answer grounded in retrieved evidence
                answer = generate_answer(question, chunks)

                retrieved_sources = "; ".join(
                    f"{chunk.get('metadata', {}).get('document_title', 'Unknown document')}"
                    f" | Page {chunk.get('metadata', {}).get('page_start', 'Unknown')}"
                    for chunk in chunks
                )

            print("\nFlyWise:")
            print(answer)

            results.append({
                "question_id": question_id,
                "question": question,
                "expected_behavior": row["expected_behavior"],
                "expected_evidence": row["expected_evidence"],
                "generated_answer": answer,
                "retrieved_sources": retrieved_sources,
                "status": "success"
            })

        except Exception as e:
            print(f"ERROR: {e}")

            results.append({
                "question_id": question_id,
                "question": question,
                "expected_behavior": row["expected_behavior"],
                "expected_evidence": row["expected_evidence"],
                "generated_answer": "",
                "retrieved_sources": "",
                "status": f"error: {e}"
            })

    # Save results
    results_df = pd.DataFrame(results)
    results_df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

    print("\n" + "=" * 65)
    print("EVALUATION COMPLETED")
    print(f"Results saved to: {OUTPUT_PATH}")
    print("=" * 65)


if __name__ == "__main__":
    main()
