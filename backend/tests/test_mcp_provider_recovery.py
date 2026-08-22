"""Regression tests for same-process LLM provider failure and automatic recovery (OPS-004)."""

import asyncio
from pathlib import Path
import tempfile
import time
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
from app.mcp import tools as mcp_tools
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
async def test_provider_failure_and_same_process_recovery():
    """Verify that when an LLM provider fails and restarts, the same MCP container automatically recovers."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_path = Path(tmp_dir) / "test_repo"
        repo_path.mkdir()
        (repo_path / "main.py").write_text("def process_data(items): return len(items)\n")

        meta = InMemoryMetaStore()
        auth = WorkspaceAuthorizationService(metadata_store=meta, workspace_roots=[Path(tmp_dir)])
        container = ApplicationContainer.create()
        container.metadata_store = meta
        container.workspace_auth = auth

        is_provider_up = True

        class FlakyContextService:
            async def generate_context_package(self, *args, **kwargs):
                if not is_provider_up:
                    raise ConnectionError("LLM endpoint connection refused (simulated provider outage)")
                mock_pkg = MagicMock()
                mock_pkg.markdown = "# Recovered Synthesis Package"
                return mock_pkg

        container.context_service = FlakyContextService()
        container.cognee_service = MagicMock()
        container.indexing_service = MagicMock()
        container.indexing_service.discover_files.return_value = [repo_path / "main.py"]
        container.indexing_service.filter_files.return_value = [repo_path / "main.py"]

        # Cycle 1: Provider is UP -> Success
        is_provider_up = True
        res1 = await mcp_tools.get_agent_context_tool("task 1", str(repo_path), container=container)
        assert res1["success"] is True
        assert "Recovered Synthesis Package" in res1["context_markdown"]

        # Cycle 2: Provider goes DOWN -> Handled error in same process
        is_provider_up = False
        t0 = time.perf_counter()
        res2 = await mcp_tools.get_agent_context_tool("task 2", str(repo_path), container=container)
        t_fail = time.perf_counter() - t0
        assert res2["success"] is False
        assert res2["error"] in ("ConnectionError", "InternalError")

        # Deterministic tools still succeed while provider is DOWN
        res_summary = await mcp_tools.get_repository_summary_tool(str(repo_path), container=container)
        assert res_summary["success"] is True

        res_ast = await mcp_tools.get_ast_call_graph_tool(str(repo_path), container=container)
        assert res_ast["success"] is True

        # Cycle 3: Provider RESTORED in same process -> Automatic Recovery
        is_provider_up = True
        res3 = await mcp_tools.get_agent_context_tool("task 3", str(repo_path), container=container)
        assert res3["success"] is True
        assert "Recovered Synthesis Package" in res3["context_markdown"]

        # Cycle 4: Repeat outage & recovery again to verify repeatability
        is_provider_up = False
        res4 = await mcp_tools.get_agent_context_tool("task 4", str(repo_path), container=container)
        assert res4["success"] is False

        is_provider_up = True
        res5 = await mcp_tools.get_agent_context_tool("task 5", str(repo_path), container=container)
        assert res5["success"] is True
        assert "Recovered Synthesis Package" in res5["context_markdown"]
