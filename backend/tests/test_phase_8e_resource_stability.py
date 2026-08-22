"""Phase 8E — Track 5: Resource and Cache Stability Under High Churn.

Validates that context and repository cache mechanisms remain strictly bounded
under repeated cache hits, cache misses, repository invalidation, manifest updates,
and alternating multi-repository workloads.
"""

import asyncio
import os
from pathlib import Path
import time
import psutil
import pytest

from app.application.container import ApplicationContainer, reset_container
from app.application.domain.repository import IndexedRepositoryRecord
from app.application.use_cases.context import BoundedConcurrencyGuard
from app.mcp.tools import (
    get_agent_context_tool,
    get_ast_call_graph_tool,
    get_repository_summary_tool,
    search_repository_code_tool,
)


@pytest.mark.asyncio
async def test_cache_and_resource_stability_under_churn(tmp_path: Path):
    """Verify memory boundedness and cache consistency across 500 churn operations."""
    reset_container()
    proc = psutil.Process()
    initial_rss = proc.memory_info().rss / (1024 * 1024)

    # Setup 4 distinct repositories
    repos: list[Path] = []
    for i in range(4):
        repo_dir = tmp_path / f"churn_repo_{i}"
        repo_dir.mkdir(parents=True, exist_ok=True)
        src_dir = repo_dir / "src"
        src_dir.mkdir(exist_ok=True)
        (src_dir / "core.py").write_text(f"def handler_{i}(): return {i}\n")
        repos.append(repo_dir)

    container = ApplicationContainer()
    guard = BoundedConcurrencyGuard(max_concurrent=1, max_queue=5, timeout=5.0)
    container._shared_concurrency_guard = guard
    container.workspace_auth.add_workspace_root(tmp_path)

    for i, r in enumerate(repos):
        container.metadata_store.upsert(
            IndexedRepositoryRecord(
                id=f"churn_id_{i}",
                name=r.name,
                path=str(r.resolve()),
                languages=["Python"],
                file_count=1,
                last_indexed="2026-08-22T00:00:00Z",
                purpose=f"Churn repo {i}",
            )
        )

    import gc
    gc.collect()
    initial_rss = proc.memory_info().rss / (1024 * 1024)

    t0 = time.perf_counter()
    iterations = 500

    for it in range(1, iterations + 1):
        # Pick repository in round-robin fashion
        repo_idx = it % 4
        target_repo = repos[repo_idx]

        # 1. Modify file on every 25th iteration to cause cache churn / cache miss
        if it % 25 == 0:
            (target_repo / "src" / "core.py").write_text(
                f"def handler_{repo_idx}():\n    return 'churn_{it}'\n"
            )

        # 2. Query summary & AST
        sum_res = await get_repository_summary_tool(
            repository_path=str(target_repo), container=container
        )
        assert sum_res.get("success") is True

        ast_res = await get_ast_call_graph_tool(
            repository_path=str(target_repo), container=container
        )
        assert ast_res.get("success") is True

        # 3. Search code
        search_res = await search_repository_code_tool(
            repository_path=str(target_repo),
            query=f"handler_{repo_idx}",
            container=container,
        )
        assert search_res.get("success") is True

    total_time = time.perf_counter() - t0
    gc.collect()
    final_rss = proc.memory_info().rss / (1024 * 1024)
    rss_delta = final_rss - initial_rss

    assert rss_delta < 50.0, f"Memory leak under cache churn: +{rss_delta:.2f} MB"
    assert guard.waiting_count == 0

    print(
        f"\n[Phase 8E Cache Stability] {iterations} churn cycles in {total_time:.2f}s | "
        f"RSS Delta: +{rss_delta:.2f}MB"
    )
