"""Regression tests for MCP and Container shared concurrency guard lifecycle (OPS-001)."""

import asyncio
from pathlib import Path
import tempfile
from typing import Any, List
from unittest.mock import MagicMock

import pytest

from app.application.container import ApplicationContainer
from app.application.domain.repository import IndexedRepositoryRecord
from app.application.dto import (
    AgentContextRequest,
    AgentContextResponse,
    ErrorResponse,
)
from app.application.ports.repository_metadata import RepositoryMetadataPort
from app.application.use_cases.context import BoundedConcurrencyGuard, ContextUseCases
from app.mcp import tools as mcp_tools
from app.services.context_cache import ContextCacheEngine
from app.services.workspace_authorization_service import WorkspaceAuthorizationService


class InMemoryMetaStore(RepositoryMetadataPort):
    def __init__(self, records: List[IndexedRepositoryRecord] | None = None) -> None:
        self._records = {r.id: r for r in (records or [])}

    def load_all(self) -> List[IndexedRepositoryRecord]:
        return list(self._records.values())

    def get_by_id(self, repo_id: str) -> IndexedRepositoryRecord | None:
        return self._records.get(repo_id)

    def get_by_path(self, path: str) -> IndexedRepositoryRecord | None:
        norm = str(Path(path).resolve())
        for r in self._records.values():
            if str(Path(r.path).resolve()) == norm:
                return r
        return None

    def upsert(self, record: IndexedRepositoryRecord) -> None:
        self._records[record.id] = record

    def delete(self, repo_id: str) -> bool:
        return self._records.pop(repo_id, None) is not None

    def count(self) -> int:
        return len(self._records)


@pytest.mark.asyncio
async def test_container_provides_shared_concurrency_guard():
    """Verify that multiple get_context_use_cases() calls share the exact same guard instance."""
    container = ApplicationContainer.create()
    uc1 = container.get_context_use_cases()
    uc2 = container.get_context_use_cases()

    assert uc1 is not uc2  # Fresh use case instances
    assert uc1._guard is uc2._guard  # Shared process-scoped guard instance
    assert uc1._guard is container.concurrency_guard


@pytest.mark.asyncio
async def test_mcp_tools_enforce_shared_concurrency_and_saturation():
    """Verify 10 parallel tool requests through container throttle to max_concurrent=1 and max_queue=5."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_path = Path(tmp_dir) / "test_repo"
        repo_path.mkdir()
        (repo_path / "main.py").write_text("def run(): pass\n")

        meta = InMemoryMetaStore()
        auth = WorkspaceAuthorizationService(metadata_store=meta, workspace_roots=[Path(tmp_dir)])
        container = ApplicationContainer.create()
        container.metadata_store = meta
        container.workspace_auth = auth

        active_count = 0
        max_active = 0
        lock = asyncio.Lock()

        # Mock context service to simulate slow async context generation
        class SlowContextService:
            async def generate_context_package(self, *args, **kwargs):
                nonlocal active_count, max_active
                async with lock:
                    active_count += 1
                    if active_count > max_active:
                        max_active = active_count
                await asyncio.sleep(0.05)
                async with lock:
                    active_count -= 1
                mock_pkg = MagicMock()
                mock_pkg.markdown = "# Generated Context"
                return mock_pkg

        container.context_service = SlowContextService()
        container.cognee_service = MagicMock()
        container.indexing_service = MagicMock()
        container.indexing_service.discover_files.return_value = [repo_path / "main.py"]
        container.indexing_service.filter_files.return_value = [repo_path / "main.py"]

        # Issue 10 concurrent requests via get_agent_context_tool
        tasks = [
            mcp_tools.get_agent_context_tool(f"task {i}", str(repo_path), container=container)
            for i in range(10)
        ]
        results = await asyncio.gather(*tasks)

        successes = [r for r in results if r.get("success") is True]
        busy_errors = [r for r in results if r.get("error") == "BusyError"]

        # Max active must never exceed 1
        assert max_active == 1
        # Total in system = 1 active + 5 queued = 6 successes, 4 BusyErrors
        assert len(successes) == 6
        assert len(busy_errors) == 4


@pytest.mark.asyncio
async def test_guard_slot_released_on_context_failure():
    """Verify that a failing request cleanly releases the guard slot for subsequent requests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_path = Path(tmp_dir) / "test_repo"
        repo_path.mkdir()
        (repo_path / "main.py").write_text("def run(): pass\n")

        meta = InMemoryMetaStore()
        auth = WorkspaceAuthorizationService(metadata_store=meta, workspace_roots=[Path(tmp_dir)])
        container = ApplicationContainer.create()
        container.metadata_store = meta
        container.workspace_auth = auth

        class FailingContextService:
            async def generate_context_package(self, *args, **kwargs):
                raise RuntimeError("Injected synthesis failure")

        container.context_service = FailingContextService()
        container.cognee_service = MagicMock()
        container.indexing_service = MagicMock()
        container.indexing_service.discover_files.return_value = [repo_path / "main.py"]
        container.indexing_service.filter_files.return_value = [repo_path / "main.py"]

        # Request 1 fails
        res1 = await mcp_tools.get_agent_context_tool("failing task", str(repo_path), container=container)
        assert res1["success"] is False
        assert res1["error"] in ("RuntimeError", "InternalError")

        # Fix service and verify slot is immediately available
        class WorkingContextService:
            async def generate_context_package(self, *args, **kwargs):
                mock_pkg = MagicMock()
                mock_pkg.markdown = "# Recovered Context"
                return mock_pkg

        container.context_service = WorkingContextService()
        res2 = await mcp_tools.get_agent_context_tool("working task", str(repo_path), container=container)
        assert res2["success"] is True
