"""
recall_demo.py — Validate cognee.recall() via CogneeService.

Purpose:
    Prove that CogneeService can retrieve previously stored information
    using hybrid search (vector + graph) over a local dataset.

Prerequisites:
    - remember_demo.py has been run successfully (data exists in dataset)
    - Ollama running with phi3:mini and nomic-embed-text:latest
    - cognee installed

Execute:
    python3.13 recall_demo.py

Expected output:
    - Retrieved results matching the query
    - Results containing relevant project information
    - No errors

Failure modes:
    - Empty dataset → no results returned
    - Ollama unavailable → embedding search fails
    - Wrong dataset name → no matching data
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from setup import get_service, DATASET_NAME, run_async


QUERIES = [
    "What is RE:Track?",
    "How does repository indexing work?",
    "What databases does the system use?",
    "What is a Context Package?",
]


async def main():
    print("=" * 60)
    print("  recall() Validation (Production Backend)")
    print("=" * 60)
    print()

    # 1. Initialize
    print("[1/3] Initializing CogneeService...")
    service = get_service()
    await service.initialize()
    print()

    # 2. Run recall queries
    print("[2/3] Running recall queries...")
    for i, query in enumerate(QUERIES, 1):
        print(f"\n  Query {i}: \"{query}\"")
        print(f"  {'-' * 50}")
        try:
            response = await service.recall(
                query_text=query,
                datasets=[DATASET_NAME],
                top_k=5,
            )
            print(f"  Results: {response.count}")
            for j, r in enumerate(response.results, 1):
                print(f"    [{j}] {r.text[:150]}")
        except Exception as e:
            print(f"  FAILED: {e}")
    print()

    # 3. Summary
    print("[3/3] Summary")
    print(f"  Dataset:    {DATASET_NAME}")
    print(f"  Queries:    {len(QUERIES)}")
    print(f"  Status:     recall() validation complete")
    print()
    print("=" * 60)
    print("  DONE — recall() validation finished")
    print("=" * 60)


if __name__ == "__main__":
    run_async(main())
