"""Phase 8D — Sustained Mixed Workload Soak Testing.

Validates process stability, RSS memory slope, file descriptor counts,
thread counts, latency bounds, and error recovery across 500+ mixed MCP tool invocations.
"""

import asyncio
import os
from pathlib import Path
import time
from typing import Any, Optional
import pytest
import psutil

from app.application.container import ApplicationContainer
from app.application.domain.repository import IndexedRepositoryRecord
from app.application.dto import (
    AgentContextRequest,
    AgentContextResponse,
    ASTCallGraphResponse,
    RepositorySummaryResponse,
)
from app.mcp import tools as mcp_tools


def _create_mock_repo(tmp_path: Path, name: str) -> Path:
    repo = tmp_path / name
    repo.mkdir(parents=True, exist_ok=True)
    src = repo / "src"
    src.mkdir(exist_ok=True)

    (src / "app.py").write_text(
        "import helper\n\n"
        "class App:\n"
        "    def run(self):\n"
        "        helper.do_work()\n"
    )
    (src / "helper.py").write_text(
        "def do_work():\n"
        "    return 'ok'\n"
    )
    return repo


from dataclasses import dataclass

@dataclass
class MockContextPackage:
    markdown: str = "# Mock Context"
    token_count: int = 100
    task_summary: str = "Mock task"


class SoakMockContextService:
    """Mock context service for high-volume soak testing."""

    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.call_count = 0

    async def generate_context_package(
        self,
        task: str,
        datasets: list[str],
        top_k: int = 15,
        repository_summary: Any = None,
        target_tokens: Optional[int] = None,
    ) -> Any:
        self.call_count += 1
        if self.should_fail:
            raise ConnectionError("Simulated LLM provider timeout")

        return MockContextPackage(
            markdown=f"# Context for {task}\nRelevant symbols: helper.do_work",
            token_count=150,
            task_summary="Soak task",
        )


@pytest.mark.asyncio
async def test_prolonged_mcp_mixed_workload_soak(tmp_path: Path):
    """Execute 500+ mixed MCP tool operations and measure resource stability."""
    proc = psutil.Process()
    initial_rss = proc.memory_info().rss / 1024 / 1024
    initial_fds = proc.num_fds() if hasattr(proc, "num_fds") else len(os.listdir("/proc/self/fd"))
    initial_threads = proc.num_threads()

    repo1 = _create_mock_repo(tmp_path, "soak_repo_1")
    repo2 = _create_mock_repo(tmp_path, "soak_repo_2")

    container = ApplicationContainer()
    container.metadata_store.upsert(
        IndexedRepositoryRecord(
            id="repo-1",
            name="soak_repo_1",
            path=str(repo1),
            languages=["Python"],
            file_count=2,
        )
    )
    container.metadata_store.upsert(
        IndexedRepositoryRecord(
            id="repo-2",
            name="soak_repo_2",
            path=str(repo2),
            languages=["Python"],
            file_count=2,
        )
    )

    from unittest.mock import MagicMock
    context_mock = SoakMockContextService()
    container.context_service = context_mock  # type: ignore
    container.cognee_service = MagicMock()  # type: ignore
    mock_idx = MagicMock()
    mock_idx.discover_files.return_value = ["src/app.py", "src/helper.py"]
    container.indexing_service = mock_idx  # type: ignore

    latencies: list[float] = []
    error_counts: dict[str, int] = {"expected_errors": 0, "unexpected_errors": 0, "busy_errors": 0}
    success_count = 0
    total_iterations = 520

    t_start = time.perf_counter()

    for i in range(total_iterations):
        t0 = time.perf_counter()
        op_type = i % 6
        target_repo = str(repo1 if i % 2 == 0 else repo2)

        # 1. Summary operation
        if op_type == 0:
            res = await mcp_tools.get_repository_summary_tool(target_repo, container=container)
            if res.get("success"):
                success_count += 1
            else:
                error_counts["unexpected_errors"] += 1
                if error_counts["unexpected_errors"] <= 3:
                    print(f"[SOAK FAIL op 0]: {res}")

        # 2. AST Call Graph operation
        elif op_type == 1:
            res = await mcp_tools.get_ast_call_graph_tool(target_repo, max_nodes=50, container=container)
            if res.get("success"):
                success_count += 1
            else:
                error_counts["unexpected_errors"] += 1
                if error_counts["unexpected_errors"] <= 3:
                    print(f"[SOAK FAIL op 1]: {res}")

        # 3. Source Search operation
        elif op_type == 2:
            res = await mcp_tools.search_repository_code_tool(target_repo, query="do_work", limit=5, container=container)
            if res.get("success"):
                success_count += 1
            else:
                error_counts["unexpected_errors"] += 1
                if error_counts["unexpected_errors"] <= 3:
                    print(f"[SOAK FAIL op 2]: {res}")

        # 4. List Repositories operation
        elif op_type == 3:
            res = await mcp_tools.list_indexed_repositories_tool(container=container)
            if res.get("success") and len(res.get("repositories", [])) >= 2:
                success_count += 1
            else:
                error_counts["unexpected_errors"] += 1
                if error_counts["unexpected_errors"] <= 3:
                    print(f"[SOAK FAIL op 3]: {res}")

        # 5. Context synthesis (with periodic provider fault injection)
        elif op_type == 4:
            # Every 50th context call, simulate temporary provider fault
            is_fault = (i % 50 == 0)
            context_mock.should_fail = is_fault

            res = await mcp_tools.get_agent_context_tool(
                f"Task query iteration {i}",
                target_repo,
                container=container,
            )
            context_mock.should_fail = False

            if is_fault:
                if res.get("success") is False and res.get("error") in ("ConnectionError", "InternalError"):
                    error_counts["expected_errors"] += 1
                else:
                    error_counts["unexpected_errors"] += 1
                    if error_counts["unexpected_errors"] <= 3:
                        print(f"[SOAK FAIL op 4 fault]: {res}")
            else:
                if res.get("success"):
                    success_count += 1
                else:
                    error_counts["unexpected_errors"] += 1
                    if error_counts["unexpected_errors"] <= 3:
                        print(f"[SOAK FAIL op 4]: {res}")

        # 6. Intentional invalid / unauthorized request (boundary test)
        elif op_type == 5:
            res = await mcp_tools.get_repository_summary_tool("/etc", container=container)
            if res.get("success") is False and res.get("error") in ("AuthorizationError", "ValidationError"):
                error_counts["expected_errors"] += 1
            else:
                error_counts["unexpected_errors"] += 1
                if error_counts["unexpected_errors"] <= 3:
                    print(f"[SOAK FAIL op 5]: {res}")

        latencies.append((time.perf_counter() - t0) * 1000)

    t_total = time.perf_counter() - t_start
    final_rss = proc.memory_info().rss / 1024 / 1024
    final_fds = proc.num_fds() if hasattr(proc, "num_fds") else len(os.listdir("/proc/self/fd"))
    final_threads = proc.num_threads()
    rss_delta = final_rss - initial_rss

    latencies.sort()
    p50 = latencies[int(len(latencies) * 0.50)]
    p90 = latencies[int(len(latencies) * 0.90)]
    p95 = latencies[int(len(latencies) * 0.95)]

    # Assertions
    assert error_counts["unexpected_errors"] == 0, f"Unexpected errors during soak: {error_counts}"
    assert success_count + error_counts["expected_errors"] == total_iterations
    assert rss_delta < 25.0, f"Memory leak detected: RSS grew by {rss_delta:.2f} MB"
    assert final_fds <= initial_fds + 5, f"FD leak detected: Initial {initial_fds}, Final {final_fds}"
    assert final_threads <= initial_threads + 2, f"Thread accumulation: Initial {initial_threads}, Final {final_threads}"
    assert p95 < 50.0, f"Latency degradation: P95 latency was {p95:.2f}ms"
