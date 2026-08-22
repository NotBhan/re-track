"""Tests for MCP Tool Exception Isolation and Error Boundary."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.application.container import ApplicationContainer
from app.mcp.tools import (
    get_agent_context_tool,
    get_ast_call_graph_tool,
    get_repository_summary_tool,
    list_indexed_repositories_tool,
    search_repository_code_tool,
)


@pytest.fixture
def mock_failing_container(tmp_path: Path):
    repo_dir = tmp_path / "valid_repo"
    repo_dir.mkdir()

    container = MagicMock(spec=ApplicationContainer)

    # Workspace auth allows repo_dir
    workspace_auth = MagicMock()
    workspace_auth.is_path_authorized.return_value = (True, None)
    container.workspace_auth = workspace_auth

    # Context Use Cases that throw unexpected runtime errors
    context_uc = MagicMock()
    context_uc.get_agent_context = AsyncMock(side_effect=RuntimeError("Database socket suddenly closed! Memory corrupted: 0xDEADBEEF"))
    context_uc.search_repository_code = AsyncMock(side_effect=ValueError("Unexpected internal token decoding error in file parser"))
    container.get_context_use_cases.return_value = context_uc

    # Repo Use Cases that throw unexpected runtime errors
    repo_uc = MagicMock()
    repo_uc.get_repository_summary = AsyncMock(side_effect=KeyError("Missing secret internal config key 'cognee_master_key'"))
    repo_uc.get_ast_call_graph = AsyncMock(side_effect=ZeroDivisionError("Division by zero in graph layout algorithm"))
    repo_uc.list_repositories = AsyncMock(side_effect=OSError("Disk hardware I/O error"))
    container.get_repository_use_cases.return_value = repo_uc

    return {
        "container": container,
        "repo_path": str(repo_dir),
    }


@pytest.mark.asyncio
async def test_get_agent_context_tool_exception_isolation(mock_failing_container):
    container = mock_failing_container["container"]
    repo_path = mock_failing_container["repo_path"]

    resp = await get_agent_context_tool(
        task_prompt="fix bug in algo",
        repository_path=repo_path,
        container=container,
    )

    assert resp["success"] is False
    assert resp["error"] == "InternalError"
    # Ensure sensitive stack trace details are not leaked in message
    assert "0xDEADBEEF" not in resp["message"]
    assert "Traceback" not in resp["message"]


@pytest.mark.asyncio
async def test_get_repository_summary_tool_exception_isolation(mock_failing_container):
    container = mock_failing_container["container"]
    repo_path = mock_failing_container["repo_path"]

    resp = await get_repository_summary_tool(
        repository_path=repo_path,
        container=container,
    )

    assert resp["success"] is False
    assert resp["error"] == "InternalError"
    assert "cognee_master_key" not in resp["message"]


@pytest.mark.asyncio
async def test_get_ast_call_graph_tool_exception_isolation(mock_failing_container):
    container = mock_failing_container["container"]
    repo_path = mock_failing_container["repo_path"]

    resp = await get_ast_call_graph_tool(
        repository_path=repo_path,
        container=container,
    )

    assert resp["success"] is False
    assert resp["error"] == "InternalError"
    assert "Division by zero" not in resp["message"]


@pytest.mark.asyncio
async def test_search_repository_code_tool_exception_isolation(mock_failing_container):
    container = mock_failing_container["container"]
    repo_path = mock_failing_container["repo_path"]

    resp = await search_repository_code_tool(
        repository_path=repo_path,
        query="MyClass",
        container=container,
    )

    assert resp["success"] is False
    assert resp["error"] == "InternalError"


@pytest.mark.asyncio
async def test_list_indexed_repositories_tool_exception_isolation(mock_failing_container):
    container = mock_failing_container["container"]

    resp = await list_indexed_repositories_tool(
        container=container,
    )

    assert resp["success"] is False
    assert resp["error"] == "InternalError"
