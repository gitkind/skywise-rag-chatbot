
import os
import pandas as pd

from retrieval import retrieve_documents
from hybrid_retrieval import hybrid_retrieve


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

DATASET_PATH = "data/flywise_evaluation_dataset_v1.csv"
OUTPUT_DIR = "data/evaluation_results"
TOP_K = 8
EVALUATION_K = 5


# Ground truth: relevant document titles and PDF pages.
# These labels are based on the supplied Air India documents.

GROUND_TRUTH = {
    "Q01": ("Air India Conditions of Carriage", [15]),
    "Q02": ("Air India Conditions of Carriage", [16]),
    "Q03": ("Air India Conditions of Carriage", [18]),
    "Q04": ("Air India Pets in Cabin Guidelines", [2]),
    "Q05": ("Air India Pets in Cabin Guidelines", [5]),
    "Q06": ("Air India Pets in Cabin Guidelines", [5]),
    "Q07": ("Air India Pets in Cabin Guidelines", [5, 6]),
    "Q08": ("Air India Pets in Cabin Guidelines", [4]),
    "Q09": ("Air India Pets in Cabin Guidelines", [6]),
    "Q10": ("Air India Conditions of Carriage", [17]),
    "Q11": ("Air India Conditions of Carriage", [15, 16, 17]),
    "Q12": ("Air India Pets in Cabin Guidelines", [2, 5]),
    "Q13": ("Air India Pets in Cabin Guidelines", [5, 6]),
    "Q14": ("Air India Conditions of Carriage", [16, 18]),
    "Q15": ("Air India Conditions of Carriage", [17]),
}


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def get_page(metadata):
    page = metadata.get("page_start")

    if page is None:
        page = metadata.get("page")

    try:
        return int(page)
    except (TypeError, ValueError):
        return None


def get_document_title(metadata):
    return str(metadata.get("document_title", "")).strip()


def evaluate_answerable(question_id, results):
    target_document, target_pages = GROUND_TRUTH[question_id]

    retrieved_pages = []
    relevant_ranks = []

    for rank, result in enumerate(results[:EVALUATION_K], start=1):
        metadata = result.get("metadata", {})

        document = get_document_title(metadata)
        page = get_page(metadata)

        # Avoid counting duplicate chunks from the same page.
        page_key = (document, page)

        if page_key not in retrieved_pages:
            retrieved_pages.append(page_key)

        if document == target_document and page in target_pages:
            relevant_ranks.append(rank)

    relevant_retrieved = sum(
        1 for document, page in retrieved_pages
        if document == target_document and page in target_pages
    )

    precision = relevant_retrieved / EVALUATION_K
    recall = relevant_retrieved / len(target_pages)

    reciprocal_rank = (
        1 / relevant_ranks[0] if relevant_ranks else 0
    )

    return {
        "precision_at_5": precision,
        "recall_at_5": recall,
        "mrr": reciprocal_rank,
        "relevant_pages_found": relevant_retrieved,
        "total_relevant_pages": len(target_pages),
    }


def run_retriever(method, question):
    if method == "Vector":
        return retrieve_documents(question, top_k=TOP_K)

    if method == "Hybrid":
        return hybrid_retrieve(question, top_k=TOP_K)

    raise ValueError(f"Unknown retrieval method: {method}")


# --------------------------------------------------
# MAIN EVALUATION
# --------------------------------------------------

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(
            f"Evaluation dataset not found: {DATASET_PATH}"
        )

    dataset = pd.read_csv(DATASET_PATH)

    detail_rows = []
    metric_rows = []

    print("\n" + "=" * 65)
    print("FLYWISE - RETRIEVAL EVALUATION")
    print("Vector RAG vs Hybrid RAG")
    print("=" * 65)

    for _, row in dataset.iterrows():

        question_id = row["question_id"]
        question = row["question"]
        question_type = row["question_type"]

        print(f"\n[{question_id}] {question}")

        for method in ["Vector", "Hybrid"]:

            print(f"Running {method} retrieval...")

            results = run_retriever(method, question)

            # Record the retrieved chunks.
            for rank, result in enumerate(results[:TOP_K], start=1):
                metadata = result.get("metadata", {})

                detail_rows.append({
                    "question_id": question_id,
                    "question_type": question_type,
                    "method": method,
                    "rank": rank,
                    "document": get_document_title(metadata),
                    "page": get_page(metadata),
                    "text": result.get("text", ""),
                    "vector_distance": result.get("distance"),
                    "rrf_score": result.get("rrf_score"),
                })

            # Calculate ranking metrics only for answerable questions.
            if question_id in GROUND_TRUTH:
                metrics = evaluate_answerable(question_id, results)

                metric_rows.append({
                    "question_id": question_id,
                    "method": method,
                    **metrics,
                })

            else:
                # Unanswerable questions are diagnostics, not Recall/MRR cases.
                metric_rows.append({
                    "question_id": question_id,
                    "method": method,
                    "precision_at_5": None,
                    "recall_at_5": None,
                    "mrr": None,
                    "relevant_pages_found": None,
                    "total_relevant_pages": None,
                })

    # --------------------------------------------------
    # SAVE RESULTS
    # --------------------------------------------------

    details = pd.DataFrame(detail_rows)
    metrics_df = pd.DataFrame(metric_rows)

    details_path = os.path.join(
        OUTPUT_DIR, "retrieval_details.csv"
    )

    metrics_path = os.path.join(
        OUTPUT_DIR, "question_metrics.csv"
    )

    summary_path = os.path.join(
        OUTPUT_DIR, "evaluation_summary.csv"
    )

    details.to_csv(details_path, index=False)
    metrics_df.to_csv(metrics_path, index=False)

    # Aggregate answerable questions only.
    answerable_metrics = metrics_df[
        metrics_df["recall_at_5"].notna()
    ]

    summary = (
        answerable_metrics
        .groupby("method")[
            ["precision_at_5", "recall_at_5", "mrr"]
        ]
        .mean()
        .reset_index()
    )

    summary.to_csv(summary_path, index=False)

    # --------------------------------------------------
    # DISPLAY SUMMARY
    # --------------------------------------------------

    print("\n" + "=" * 65)
    print("FINAL EVALUATION SUMMARY")
    print("=" * 65)

    print(summary.to_string(index=False))

    print("\nUnanswerable questions:")
    print("These are saved as retrieval diagnostics.")
    print("They are not included in Recall@5, Precision@5 or MRR.")

    print("\nFiles generated:")
    print(details_path)
    print(metrics_path)
    print(summary_path)

    print("\nEvaluation completed.")


if __name__ == "__main__":
    main()
