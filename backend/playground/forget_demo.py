"""
forget_demo.py — Validate cognee.forget() via CogneeService.

Purpose:
    Prove that CogneeService can remove stored information from a dataset,
    cleaning up vectors, graph nodes, relationships, and metadata.

Prerequisites:
    - remember_demo.py has been run successfully (data exists in dataset)
    - Ollama running with phi3:mini and nomic-embed-text:latest
    - cognee installed

Execute:
    python3.13 forget_demo.py

Expected output:
    - Confirmation that forget() ran without errors
    - Recall after forget returns fewer or no results
    - No errors

Failure modes:
    - Dataset doesn't exist → nothing to forget
    - Ollama unavailable → verification recall fails
    - API signature mismatch → parameter errors
    - Partial deletion → some data remains
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from setup import get_service, DATASET_NAME, run_async


async def main():
    print("=" * 60)
    print("  forget() Validation (Production Backend)")
    print("=" * 60)
    print()

    # 1. Initialize
    print("[1/4] Initializing CogneeService...")
    service = get_service()
    await service.initialize()
    print()

    # 2. Verify data exists before forgetting
    print("[2/4] Verifying data exists before forget()...")
    try:
        before = await service.recall(
            query_text="What is RE:Track?",
            datasets=[DATASET_NAME],
            top_k=3,
        )
        print(f"  Before forget: {before.count} result(s)")
    except Exception as e:
        print(f"  Pre-forget recall failed: {e}")
        before = None
    print()

    # 3. Forget the dataset
    print(f"[3/4] Forgetting dataset '{DATASET_NAME}'...")
    try:
        await service.forget(dataset=DATASET_NAME)
        print("  forget() completed successfully")
    except Exception as e:
        print(f"  forget() failed: {e}")
    print()

    # 4. Verify data is gone
    print("[4/4] Verifying data was removed...")
    try:
        after = await service.recall(
            query_text="What is RE:Track?",
            datasets=[DATASET_NAME],
            top_k=3,
        )
        print(f"  After forget: {after.count} result(s)")
        before_count = before.count if before else 0
        if after.count < before_count:
            print("  Data was successfully removed")
        elif after.count == 0:
            print("  Dataset is empty — forget() worked completely")
        else:
            print("  Same number of results — verify forget() behavior")
    except Exception as e:
        print(f"  Post-forget recall failed (may indicate deletion): {e}")
    print()

    print("=" * 60)
    print("  DONE — forget() validation finished")
    print("=" * 60)


if __name__ == "__main__":
    run_async(main())
