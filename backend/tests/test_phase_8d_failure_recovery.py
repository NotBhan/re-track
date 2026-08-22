"""Phase 8D — Failure Recovery Matrix.

Validates that RE:Track recovers gracefully and automatically from repeated LLM provider outages,
queued request cancellations, active worker failures, authorization errors, and malformed inputs
without permanent state corruption or process termination.
"""

import asyncio
from pathlib import Path
import time
from typing import Any, Optional
from unittest.mock import MagicMock
import pytest

from app.application.container import ApplicationContainer
from app.application.domain.repository import IndexedRepositoryRecord
from app.application.dto import AgentContextRequest, AgentContextResponse
from app.application.use_cases.context import BoundedConcurrencyGuard, ContextUseCases
from app.mcp import tools as mcp_tools


def _create_mock_repo(tmp_path: Path, name: str = "recovery_repo") -> Path:
    repo = tmp_path / name
    repo.mkdir(parents=True, exist_ok=True)
    src = repo / "src"
    src.mkdir(exist_ok=True)

    (src / "service.py").write_text(
        "class Service:\n"
        "    def process(self):\n"
        "        return True\n"
    )
    return repo


from dataclasses import dataclass

@dataclass
class MockContextPackage:
    markdown: str = "# Mock Context"
    token_count: int = 100
    task_summary: str = "Mock task"


class ControlledContextService:
    """Mock context service with controllable latency and failure toggling."""

    def __init__(self):
        self.is_healthy = True
        self.delay = 0.0

    async def generate_context_package(
        self,
        task: str,
        datasets: list[str],
        top_k: int = 15,
        repository_summary: Any = None,
        target_tokens: Optional[int] = None,
    ) -> Any:
        if self.delay > 0:
            await asyncio.sleep(self.delay)

        if not self.is_healthy:
            raise ConnectionError("LLM provider connection refused: ConnectionResetError")

        return MockContextPackage(
            markdown=f"# Context for {task}",
            token_count=100,
            task_summary="Recovery task",
        )


@pytest.mark.asyncio
async def test_repeated_llm_provider_failure_and_recovery(tmp_path: Path):
    """Scenario 1 & 2: LLM provider fails and recovers repeatedly across 5 cycles."""
    repo = _create_mock_repo(tmp_path)
    container = ApplicationContainer()
    container.metadata_store.upsert(
        IndexedRepositoryRecord(
            id="repo-1",
            name="recovery_repo",
            path=str(repo),
            languages=["Python"],
            file_count=1,
        )
    )

    mock_service = ControlledContextService()
    container.context_service = mock_service  # type: ignore
    container.cognee_service = MagicMock()  # type: ignore
    mock_idx = MagicMock()
    mock_idx.discover_files.return_value = ["src/service.py"]
    container.indexing_service = mock_idx  # type: ignore

    for cycle in range(5):
        # 1. UP
        mock_service.is_healthy = True
        res_up = await mcp_tools.get_agent_context_tool(f"Task cycle {cycle} UP", str(repo), container=container)
        assert res_up["success"] is True, f"Cycle {cycle} UP failed: {res_up}"

        # 2. DOWN
        mock_service.is_healthy = False
        res_down = await mcp_tools.get_agent_context_tool(f"Task cycle {cycle} DOWN", str(repo), container=container)
        assert res_down["success"] is False
        assert res_down["error"] in ("ConnectionError", "InternalError")

        # Deterministic tools still succeed while LLM is down
        res_summary = await mcp_tools.get_repository_summary_tool(str(repo), container=container)
        assert res_summary["success"] is True

    # Final recovery
    mock_service.is_healthy = True
    res_final = await mcp_tools.get_agent_context_tool("Final task", str(repo), container=container)
    assert res_final["success"] is True


@pytest.mark.asyncio
async def test_active_failure_with_queued_requests(tmp_path: Path):
    """Scenario 3 & 5: Active request fails while another request is queued -> queued request proceeds."""
    repo = _create_mock_repo(tmp_path)
    container = ApplicationContainer()
    container.metadata_store.upsert(
        IndexedRepositoryRecord(
            id="repo-1",
            name="recovery_repo",
            path=str(repo),
            languages=["Python"],
            file_count=1,
        )
    )

    call_count = 0

    class AlternatingFailureContextService:
        async def generate_context_package(
            self,
            task: str,
            datasets: list[str],
            top_k: int = 15,
            repository_summary: Any = None,
            target_tokens: Optional[int] = None,
        ) -> Any:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Active request delays then fails
                await asyncio.sleep(0.1)
                raise RuntimeError("Primary worker crashed")
            else:
                # Queued request delays then succeeds
                await asyncio.sleep(0.05)
                return MockContextPackage(
                    markdown="# Success",
                    token_count=100,
                    task_summary="Queued task",
                )

    container.context_service = AlternatingFailureContextService()  # type: ignore
    container.cognee_service = MagicMock()  # type: ignore
    mock_idx = MagicMock()
    mock_idx.discover_files.return_value = ["src/service.py"]
    container.indexing_service = mock_idx  # type: ignore

    # Launch two requests concurrently
    task1 = asyncio.create_task(mcp_tools.get_agent_context_tool("Request 1 (fails)", str(repo), container=container))
    await asyncio.sleep(0.02)  # ensure task1 acquires slot
    task2 = asyncio.create_task(mcp_tools.get_agent_context_tool("Request 2 (queued)", str(repo), container=container))

    res1, res2 = await asyncio.gather(task1, task2)
    assert res1["success"] is False
    assert res1["error"] in ("RuntimeError", "InternalError")
    assert res2["success"] is True


@pytest.mark.asyncio
async def test_queued_request_cancellation_preserves_guard(tmp_path: Path):
    """Scenario 4: Cancelling a queued request frees the queue counter without leaking capacity."""
    guard = BoundedConcurrencyGuard(max_concurrent=1, max_queue=2, timeout=5.0)

    # Acquire active slot
    acquired, _ = await guard.acquire()
    assert acquired is True

    # Start a queued request in a separate task
    queued_task = asyncio.create_task(guard.acquire())
    await asyncio.sleep(0.05)
    assert guard.waiting_count == 1

    # Cancel the queued task
    queued_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await queued_task

    assert guard.waiting_count == 0

    # Release active slot
    guard.release()

    # Verify guard is completely healthy
    next_acquire, _ = await guard.acquire()
    assert next_acquire is True
    guard.release()


@pytest.mark.asyncio
async def test_authorization_failure_followed_by_valid_request(tmp_path: Path):
    """Scenario 6: Authorization rejection does not poison subsequent valid requests."""
    repo = _create_mock_repo(tmp_path)
    container = ApplicationContainer()
    container.metadata_store.upsert(
        IndexedRepositoryRecord(
            id="repo-1",
            name="recovery_repo",
            path=str(repo),
            languages=["Python"],
            file_count=1,
        )
    )

    # 1. Unauthorized request
    res_auth = await mcp_tools.get_repository_summary_tool("/etc", container=container)
    assert res_auth["success"] is False
    assert res_auth["error"] in ("AuthorizationError", "ValidationError")

    # 2. Valid request immediately succeeds
    res_valid = await mcp_tools.get_repository_summary_tool(str(repo), container=container)
    assert res_valid["success"] is True


@pytest.mark.asyncio
async def test_malformed_arguments_followed_by_valid_request(tmp_path: Path):
    """Scenario 7 & 8: Malformed arguments and non-existent paths fail cleanly and allow valid calls."""
    repo = _create_mock_repo(tmp_path)
    container = ApplicationContainer()
    container.metadata_store.upsert(
        IndexedRepositoryRecord(
            id="repo-1",
            name="recovery_repo",
            path=str(repo),
            languages=["Python"],
            file_count=1,
        )
    )

    # Empty prompt
    res_bad = await mcp_tools.get_agent_context_tool("", str(repo), container=container)
    assert res_bad["success"] is False
    assert res_bad["error"] == "ValidationError"

    # Non-existent path
    res_missing = await mcp_tools.get_repository_summary_tool("/tmp/definitely_missing_path_12345", container=container)
    assert res_missing["success"] is False
    assert res_missing["error"] == "ValidationError"

    # Valid search request
    res_valid = await mcp_tools.search_repository_code_tool(str(repo), query="Service", container=container)
    assert res_valid["success"] is True
