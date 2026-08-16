"""
setup.py — Cognee playground bootstrap.

Purpose:
    Centralizes Cognee configuration for the validation playground scripts.
    Every demo script imports initialize_cognee() from this module.

    Uses the production CogneeService for initialization.

Prerequisites:
    - Ollama running on localhost:11434
    - Models pulled: phi3:mini, nomic-embed-text:latest
    - cognee installed (pip install cognee)
    - kuzu installed (bundled with cognee)

Usage:
    from setup import get_service, DATASET_NAME

    service = get_service()
    await service.initialize()

Expected output:
    "Cognee initialized successfully"

Failure modes:
    - Ollama not running → connection refused
    - Model missing → model not found error
    - Database lock → another process using the same DB path
"""

import os
import sys
import asyncio
from pathlib import Path

# Ensure the backend/app package is importable
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.services.cognee_service import CogneeService
from app.config.settings import get_settings
from app.core.logging import setup_logging

# ── Dataset name used across all playground scripts ──
DATASET_NAME = "retrack_playground"

# ── Module-level service instance ──
_service: CogneeService | None = None


def get_service() -> CogneeService:
    """Return the CogneeService singleton, creating it if needed."""
    global _service
    if _service is None:
        setup_logging()
        _service = CogneeService()
    return _service


def run_async(coro):
    """Helper to run an async function from a sync script."""
    asyncio.run(coro)


if __name__ == "__main__":
    import socket

    settings = get_settings()

    print("=" * 60)
    print("  Cognee Playground Setup (Production Backend)")
    print("=" * 60)
    print()

    # Check Ollama
    if not settings.ollama.check_connection():
        print("ERROR: Ollama is not reachable at", settings.ollama.base_url)
        print("       Start it with: ollama serve")
        sys.exit(1)

    print(f"  LLM provider:     ollama")
    print(f"  LLM model:        {settings.ollama.llm_model}")
    print(f"  Embedding model:  {settings.ollama.embedding_model}")
    print(f"  Vector DB:        {settings.storage.vector_db}")
    print(f"  Graph DB:         {settings.storage.graph_db}")
    print(f"  Relational DB:    {settings.storage.relational_db}")
    print(f"  Data root:        {settings.storage.data_root}")
    print(f"  System root:      {settings.storage.system_root}")
    print()

    async def _init():
        svc = get_service()
        await svc.initialize()
        print("Cognee initialized successfully.")

    run_async(_init())
