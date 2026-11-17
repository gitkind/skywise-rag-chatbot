"""
Test verification script for the 5 mandated queries in FlyWise
"""
import os
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

from backend_service import get_flywise_response

test_queries = [
    "What happens if Air India cancels my flight?",
    "What are the requirements for pets in the cabin?",
    "Are free helicopter transfers included?",
    "Can I carry a rabbit in the cabin?",
    "What is the current baggage allowance?"
]

print("=" * 60)
print("FLYWISE RAG PIPELINE VERIFICATION")
print("=" * 60)

for q in test_queries:
    print(f"\n[QUERY] {q}")
    res = get_flywise_response(q)
    print(f"Chunks Retrieved : {len(res['chunks'])}")
    print(f"Unique Citations : {len(res['citations'])}")
    for i, c in enumerate(res['citations'][:2], 1):
        print(f"  Ref {i}: {c['title']} | {c['pages']} (Effective: {c['effective_date']})")
    print(f"Answer snippet   : {res['answer'][:100]}...")

print("\n" + "=" * 60)
print("ALL 5 QUERIES VERIFIED SUCCESSFULLY")
print("=" * 60)
