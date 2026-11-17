"""
Updated Backend Service Bridge with Relevance Guardrails, Re-ranking, and Citation Validation
"""

import os
from typing import Dict, Any

# Ensure HuggingFace loads offline embeddings if cached
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from dotenv import load_dotenv
load_dotenv()

from hybrid_retrieval import hybrid_retrieve, bm25, embedding_model, collection
from guardrails import assess_input_relevance, rerank_chunks, verify_and_filter_citations


def is_openai_configured() -> bool:
    """Checks whether OPENAI_API_KEY is present in the environment."""
    return bool(os.getenv("OPENAI_API_KEY"))


def get_flywise_response(question: str, top_k: int = 5) -> Dict[str, Any]:
    """
    Executes Guarded RAG Pipeline:
    1. Input Guardrail: Evaluates semantic and lexical relevance against Air India corpus.
    2. Hybrid Retrieval: Queries ChromaDB vector store + BM25 index with RRF.
    3. Re-ranking: Re-scores candidate chunks with keyword density and passenger priority.
    4. Generation: Calls grounded LLM (gpt-5.5) using verified context.
    5. Output Guardrail: Validates citations and detects abstentions, preventing hallucinated citations.
    """
    cleaned_q = question.strip() if question else ""
    if not cleaned_q:
        return {
            "answer": "Please ask a question about Air India policies.",
            "chunks": [],
            "citations": [],
            "is_abstention": False,
            "evaluation": {"status": "empty_query"},
            "error": None
        }

    # Step 1: Input Guardrail Check
    relevance_eval = assess_input_relevance(
        cleaned_q,
        bm25_model=bm25,
        embedding_model=embedding_model,
        chroma_collection=collection
    )

    # If query is completely ungrounded in Air India corpus (e.g. unknown term like "hooyian")
    if not relevance_eval["is_relevant"]:
        abstain_text = (
            "I couldn't find enough information in the supplied Air India policy documents to answer this confidently.\n\n"
            f"The query refers to terms ({', '.join(relevance_eval['content_tokens'])}) that do not appear in or relate "
            "to any supplied Air India policy guidelines. Therefore, no policy claims or entitlements can be established."
        )
        return {
            "answer": abstain_text,
            "chunks": [],
            "citations": [],
            "is_abstention": True,
            "evaluation": {
                "guardrail": "input_relevance_abstention",
                "max_cos_sim": round(relevance_eval["max_cos_sim"], 4),
                "max_bm25": round(relevance_eval["max_content_bm25"], 2)
            },
            "error": None
        }

    # Step 2: Hybrid Retrieval
    try:
        raw_chunks = hybrid_retrieve(cleaned_q, top_k=top_k * 2)
    except Exception as e:
        return {
            "answer": f"Retrieval error: {str(e)}",
            "chunks": [],
            "citations": [],
            "is_abstention": False,
            "evaluation": {"status": "retrieval_error"},
            "error": str(e)
        }

    # Step 3: Re-ranking
    reranked_chunks = rerank_chunks(cleaned_q, raw_chunks, top_k=top_k)

    if not reranked_chunks:
        return {
            "answer": "I couldn't find enough information in the supplied Air India policy documents to answer this confidently.",
            "chunks": [],
            "citations": [],
            "is_abstention": True,
            "evaluation": {"status": "zero_chunks_after_rerank"},
            "error": None
        }

    # Step 4: Generation via OpenAI if configured
    if not is_openai_configured():
        return {
            "answer": (
                "**Notice:** OpenAI API credentials (`OPENAI_API_KEY`) are not currently set in `.env`.\n\n"
                f"Retrieved and re-ranked **{len(reranked_chunks)} policy chunks** successfully."
            ),
            "chunks": reranked_chunks,
            "citations": [],
            "is_abstention": False,
            "evaluation": {"status": "offline_mode"},
            "error": "OPENAI_API_KEY_MISSING"
        }

    try:
        from generation import generate_answer
        answer = generate_answer(cleaned_q, reranked_chunks)

        # Step 5: Output Guardrail (verify citations and detect abstention)
        citations, is_abstention = verify_and_filter_citations(answer, reranked_chunks)

        return {
            "answer": answer,
            "chunks": reranked_chunks,
            "citations": citations,
            "is_abstention": is_abstention,
            "evaluation": {
                "guardrail": "passed",
                "reranked_count": len(reranked_chunks),
                "citations_verified": len(citations),
                "is_abstention": is_abstention,
                "max_cos_sim": round(relevance_eval["max_cos_sim"], 4)
            },
            "error": None
        }

    except Exception as e:
        return {
            "answer": f"Generation error: {str(e)}",
            "chunks": reranked_chunks,
            "citations": [],
            "is_abstention": False,
            "evaluation": {"status": "generation_exception"},
            "error": str(e)
        }
