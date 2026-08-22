"""Phase 8E — Track 1: Long-Duration 3,000-Operation MCP Soak Validation.

Executes 3,000 mixed MCP tool calls across multiple dynamic repositories
(including identical basenames, ignored files, and internal symlinks) with periodic
fault injection, collecting telemetry every 100 requests.
"""

import asyncio
import json
import os
from pathlib import Path
import random
import sys
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import psutil
import pytest

from app.application.container import ApplicationContainer, reset_container
from app.application.domain.repository import IndexedRepositoryRecord
from app.application.use_cases.context import BoundedConcurrencyGuard, ContextUseCases
from app.mcp.tools import (
    get_agent_context_tool,
    get_ast_call_graph_tool,
    get_repository_summary_tool,
    list_indexed_repositories_tool,
    search_repository_code_tool,
)


class MockContextPackage:
    def __init__(self, markdown: str) -> None:
        self.markdown = markdown


@pytest.mark.asyncio
async def test_prolonged_3000_operations_mcp_soak(tmp_path: Path):
    """Execute 3,000 operations across diverse repositories with telemetry profiling."""
    reset_container()
    proc = psutil.Process()
    initial_rss = proc.memory_info().rss / (1024 * 1024)
    initial_fds = proc.num_fds() if hasattr(proc, "num_fds") else 0
    initial_threads = proc.num_threads()

    # Create 3 test repositories:
    # 1. repo_a in workspace_1
    # 2. repo_a in workspace_2 (identical basename)
    # 3. repo_sym in workspace_1 with internal symlink and ignored files
    ws1 = tmp_path / "workspace_1"
    ws2 = tmp_path / "workspace_2"
    ws1.mkdir()
    ws2.mkdir()

    repo1 = ws1 / "repo_a"
    repo2 = ws2 / "repo_a"
    repo3 = ws1 / "repo_sym"

    for r in (repo1, repo2, repo3):
        r.mkdir(parents=True, exist_ok=True)
        src = r / "src"
        src.mkdir(exist_ok=True)
        (src / "app.py").write_text(
            "import helper\n\n"
            "class Application:\n"
            "    def run(self):\n"
            "        return helper.compute(42)\n"
        )
        (src / "helper.py").write_text(
            "def compute(val: int) -> int:\n"
            "    return val * 2\n"
        )

    # Add ignored files to repo3
    (repo3 / ".gitignore").write_text("*.log\ntemp/\n")
    (repo3 / "debug.log").write_text("ignore this log file")

    # Add internal symlink in repo3: src/sym_helper.py -> src/helper.py
    sym_file = repo3 / "src" / "sym_helper.py"
    try:
        sym_file.symlink_to(repo3 / "src" / "helper.py")
    except OSError:
        pass  # Windows or unprivileged fallback

    container = ApplicationContainer()
    guard = BoundedConcurrencyGuard(max_concurrent=1, max_queue=10, timeout=10.0)
    container._shared_concurrency_guard = guard

    # Authorize repositories
    container.workspace_auth.add_workspace_root(ws1)
    container.workspace_auth.add_workspace_root(ws2)
    for idx, r in enumerate((repo1, repo2, repo3)):
        rec = IndexedRepositoryRecord(
            id=f"repo_id_{idx}",
            name=r.name,
            path=str(r.resolve()),
            languages=["Python"],
            file_count=2,
            last_indexed="2026-08-22T00:00:00Z",
            purpose=f"Test repo {r.name}",
        )
        container.metadata_store.upsert(rec)

    # Mock context service to avoid external LLM latency during 3,000 soak iterations
    mock_context_service = MagicMock()
    mock_context_service.generate_context_package = AsyncMock(
        return_value=MockContextPackage(markdown="# Synthesized Context\n- app.py\n- helper.py")
    )
    container.context_service = mock_context_service
    container.cognee_service = MagicMock()
    container.indexing_service = MagicMock()
    container.indexing_service.discover_files.return_value = [
        str(repo1 / "src" / "app.py"),
        str(repo1 / "src" / "helper.py"),
    ]

    import gc
    gc.collect()
    initial_rss = proc.memory_info().rss / (1024 * 1024)
    initial_fds = proc.num_fds() if hasattr(proc, "num_fds") else 0
    initial_threads = proc.num_threads()

    total_ops = 3000
    repos = [str(repo1), str(repo2), str(repo3)]
    tools = [
        "get_repository_summary",
        "get_ast_call_graph",
        "search_repository_code",
        "list_indexed_repositories",
        "get_agent_context",
    ]

    tool_latencies: dict[str, list[float]] = {t: [] for t in tools}
    tool_counts: dict[str, int] = {t: 0 for t in tools}
    snapshots: list[dict[str, Any]] = []

    success_count = 0
    fault_count = 0
    start_time = time.perf_counter()

    for op_idx in range(1, total_ops + 1):
        chosen_tool = random.choice(tools)
        chosen_repo = random.choice(repos)

        # Periodically mutate a file every 150 operations to simulate real developer activity
        if op_idx % 150 == 0:
            target_repo = Path(chosen_repo)
            (target_repo / "src" / "helper.py").write_text(
                f"def compute(val: int) -> int:\n    return val * {op_idx}\n"
            )

        # 5% fault injection: invalid path for path-dependent tools
        inject_fault = (op_idx % 20 == 0) and (chosen_tool != "list_indexed_repositories")
        repo_arg = "/unauthorized/system/path" if inject_fault else chosen_repo

        t0 = time.perf_counter()
        try:
            if chosen_tool == "get_repository_summary":
                res = await get_repository_summary_tool(repository_path=repo_arg, container=container)
            elif chosen_tool == "get_ast_call_graph":
                res = await get_ast_call_graph_tool(repository_path=repo_arg, container=container)
            elif chosen_tool == "search_repository_code":
                res = await search_repository_code_tool(
                    repository_path=repo_arg, query="compute", container=container
                )
            elif chosen_tool == "list_indexed_repositories":
                res = await list_indexed_repositories_tool(container=container)
            elif chosen_tool == "get_agent_context":
                res = await get_agent_context_tool(
                    task_prompt="Refactor compute function",
                    repository_path=repo_arg,
                    container=container,
                )
            latency_ms = (time.perf_counter() - t0) * 1000
            tool_latencies[chosen_tool].append(latency_ms)
            tool_counts[chosen_tool] += 1

            if inject_fault:
                fault_count += 1
                assert res.get("success") is False
                assert res.get("error") in ("AuthorizationError", "ValidationError")
            else:
                success_count += 1
                assert res.get("success") is True, f"Failed on op {op_idx}, tool {chosen_tool}: {res}"
        except Exception as e:
            pytest.fail(f"Unhandled exception during soak op {op_idx} ({chosen_tool}): {e}")

        # Telemetry snapshot every 100 operations
        if op_idx % 100 == 0:
            current_rss = proc.memory_info().rss / (1024 * 1024)
            current_fds = proc.num_fds() if hasattr(proc, "num_fds") else 0
            current_threads = proc.num_threads()
            snapshots.append({
                "op": op_idx,
                "rss_mb": current_rss,
                "fds": current_fds,
                "threads": current_threads,
                "guard_waiting": guard.waiting_count,
            })

    total_duration = time.perf_counter() - start_time
    gc.collect()
    final_rss = proc.memory_info().rss / (1024 * 1024)
    final_fds = proc.num_fds() if hasattr(proc, "num_fds") else 0
    final_threads = proc.num_threads()

    rss_growth = final_rss - initial_rss
    peak_rss = max(s["rss_mb"] for s in snapshots)

    # Compute latencies
    all_latencies = [lat for lats in tool_latencies.values() for lat in lats]
    all_latencies.sort()
    p50 = all_latencies[int(len(all_latencies) * 0.5)]
    p95 = all_latencies[int(len(all_latencies) * 0.95)]
    p99 = all_latencies[int(len(all_latencies) * 0.99)]

    # Assertions for long duration soak gate
    assert success_count + fault_count == total_ops
    assert rss_growth < 50.0, f"Unbounded memory growth detected: +{rss_growth:.2f} MB (peak={peak_rss:.2f}MB)"
    if hasattr(proc, "num_fds"):
        assert final_fds <= initial_fds + 5, f"FD leak detected: initial={initial_fds}, final={final_fds}"
    assert final_threads <= initial_threads + 2, f"Thread accumulation: initial={initial_threads}, final={final_threads}"
    assert guard.waiting_count == 0, f"Queue buildup in concurrency guard: {guard.waiting_count}"
    assert p50 < 20.0, f"P50 latency degraded: {p50:.2f}ms"
    assert p95 < 100.0, f"P95 latency degraded: {p95:.2f}ms"

    print(
        f"\n[Phase 8E Soak Telemetry] {total_ops} ops in {total_duration:.2f}s | "
        f"RSS: {initial_rss:.1f}MB -> {final_rss:.1f}MB (+{rss_growth:.1f}MB) | "
        f"FDs: {initial_fds} -> {final_fds} | Threads: {initial_threads} -> {final_threads} | "
        f"P50: {p50:.2f}ms, P95: {p95:.2f}ms, P99: {p99:.2f}ms"
    )
