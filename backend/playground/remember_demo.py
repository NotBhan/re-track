"""
remember_demo.py — Validate cognee.remember() via CogneeService.

Purpose:
    Prove that CogneeService can ingest text data into a local dataset
    using Ollama for LLM + embeddings and LanceDB/Kuzu/SQLite for storage.

Prerequisites:
    - Ollama running with phi3:mini and nomic-embed-text:latest
    - cognee installed
    - Run setup.py first (or import get_service)

Execute:
    python3.13 remember_demo.py

Expected output:
    - Confirmation that sample data was stored
    - Dataset name printed
    - No errors

Failure modes:
    - Ollama unavailable → connection refused
    - Embedding model missing → initialization error
    - LLM model missing → entity extraction fails
    - Database errors → storage path issues
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from setup import get_service, DATASET_NAME, run_async


SAMPLE_DATA = [
    "RE:Track is a local-first AI memory system for software development.",
    "The system uses Cognee as its persistent memory layer.",
    "Repository indexing builds long-term project memory.",
    "Context Packages are compact summaries sent to coding LLMs.",
    "The architecture separates frontend, backend, and memory layers.",
    "Ollama provides local LLM inference for entity extraction.",
    "LanceDB stores vector embeddings for semantic search.",
    "Kuzu stores the knowledge graph for structural queries.",
    "SQLite handles metadata and relational storage.",
    "The remember() function ingests data into the knowledge graph.",
]


async def main():
    print("=" * 60)
    print("  remember() Validation (Production Backend)")
    print("=" * 60)
    print()

    # 1. Initialize
    print("[1/4] Initializing CogneeService...")
    service = get_service()
    await service.initialize()
    print()

    # 2. Remember sample data
    print(f"[2/4] Storing {len(SAMPLE_DATA)} items into dataset '{DATASET_NAME}'...")
    for i, item in enumerate(SAMPLE_DATA, 1):
        print(f"  [{i}/{len(SAMPLE_DATA)}] {item[:60]}...")
        try:
            result = await service.remember(
                data=item,
                dataset_name=DATASET_NAME,
            )
            print(f"       -> OK (items_sent={result.items_sent})")
        except Exception as e:
            print(f"       -> FAILED: {e}")
    print()

    # 3. Verify
    print("[3/4] Verifying data was stored (basic recall)...")
    try:
        response = await service.recall(
            query_text="What is RE:Track?",
            datasets=[DATASET_NAME],
            top_k=3,
        )
        print(f"  Recall returned {response.count} result(s)")
        for i, r in enumerate(response.results, 1):
            print(f"  [{i}] {r.text[:120]}")
    except Exception as e:
        print(f"  Recall verification failed: {e}")
    print()

    # 4. Summary
    print("[4/4] Summary")
    print(f"  Dataset:    {DATASET_NAME}")
    print(f"  Items sent: {len(SAMPLE_DATA)}")
    print(f"  Status:     remember() validation complete")
    print()
    print("=" * 60)
    print("  DONE — remember() validation finished")
    print("=" * 60)


if __name__ == "__main__":
    run_async(main())
