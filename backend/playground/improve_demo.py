"""
improve_demo.py — Validate cognee.improve() via CogneeService.

Purpose:
    Prove that CogneeService can enrich and refine existing memory
    by analyzing the knowledge graph, merging similar concepts,
    and generating higher-level summaries.

Prerequisites:
    - remember_demo.py has been run successfully (data exists in dataset)
    - Ollama running with phi3:mini and nomic-embed-text:latest
    - cognee installed

Execute:
    python3.13 improve_demo.py

Expected output:
    - Confirmation that improve() ran without errors
    - No crashes or API mismatches

Failure modes:
    - Empty dataset → nothing to improve
    - Ollama unavailable → LLM-dependent steps fail
    - API signature mismatch → parameter errors
    - Long execution time → improve() is computationally heavy
"""

import asyncio
import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))

from setup import get_service, DATASET_NAME, run_async


async def main():
    print("=" * 60)
    print("  improve() Validation (Production Backend)")
    print("=" * 60)
    print()

    # 1. Initialize
    print("[1/3] Initializing CogneeService...")
    service = get_service()
    await service.initialize()
    print()

    # 2. Run improve
    print("[2/3] Running improve()...")
    print("  (This may take a while — improve() is computationally heavy)")
    print()
    start = time.time()
    try:
        result = await service.improve()
        elapsed = time.time() - start
        print(f"  improve() completed in {elapsed:.1f}s")
        print(f"  Result type: {type(result).__name__}")
        if result is not None:
            print(f"  Result: {str(result)[:200]}")
    except Exception as e:
        elapsed = time.time() - start
        print(f"  improve() failed after {elapsed:.1f}s: {e}")
    print()

    # 3. Verify improvement
    print("[3/3] Verifying improvement with recall...")
    try:
        response = await service.recall(
            query_text="What is RE:Track?",
            datasets=[DATASET_NAME],
            top_k=3,
        )
        print(f"  Post-improve recall returned {response.count} result(s)")
        for i, r in enumerate(response.results, 1):
            print(f"    [{i}] {r.text[:150]}")
    except Exception as e:
        print(f"  Post-improve recall failed: {e}")
    print()

    print("=" * 60)
    print("  DONE — improve() validation finished")
    print("=" * 60)


if __name__ == "__main__":
    run_async(main())
