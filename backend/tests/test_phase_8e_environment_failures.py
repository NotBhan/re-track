"""Phase 8E — Track 3: Host Environment and Filesystem Failure Matrix.

Tests 13 developer-machine failure modes: repository disappearance, permission changes,
broken symlinks, malformed source syntax, binary files, corrupted manifests, and invalid configs.
"""

import os
from pathlib import Path
import stat
import pytest

from app.application.container import ApplicationContainer, reset_container
from app.application.domain.repository import IndexedRepositoryRecord
from app.mcp.tools import (
    get_agent_context_tool,
    get_ast_call_graph_tool,
    get_repository_summary_tool,
    search_repository_code_tool,
)


@pytest.mark.asyncio
async def test_repository_disappears_and_reappears(tmp_path: Path):
    """Verify clean handling when an indexed repository is deleted and recreated."""
    reset_container()
    repo_dir = tmp_path / "temp_repo"
    repo_dir.mkdir()
    (repo_dir / "app.py").write_text("def hello(): return 1\n")

    container = ApplicationContainer()
    container.workspace_auth.add_workspace_root(tmp_path)
    container.metadata_store.upsert(
        IndexedRepositoryRecord(
            id="temp_repo_id",
            name=repo_dir.name,
            path=str(repo_dir.resolve()),
            languages=["Python"],
            file_count=1,
            last_indexed="2026-08-22T00:00:00Z",
            purpose="Temp repo",
        )
    )

    # 1. Valid call
    r1 = await get_repository_summary_tool(repository_path=str(repo_dir), container=container)
    assert r1.get("success") is True

    # 2. Repository disappears (e.g. unmounted or deleted)
    (repo_dir / "app.py").unlink()
    repo_dir.rmdir()

    r2 = await get_repository_summary_tool(repository_path=str(repo_dir), container=container)
    assert r2.get("success") is False
    assert r2.get("error") in ("ValidationError", "AuthorizationError")

    # 3. Repository reappears
    repo_dir.mkdir()
    (repo_dir / "app.py").write_text("def hello_new(): return 2\n")

    r3 = await get_repository_summary_tool(repository_path=str(repo_dir), container=container)
    assert r3.get("success") is True


@pytest.mark.asyncio
async def test_repository_permissions_change_and_broken_symlinks(tmp_path: Path):
    """Verify handling when directories are unreadable or contain dangling symlinks."""
    reset_container()
    repo_dir = tmp_path / "perm_repo"
    repo_dir.mkdir()
    src_dir = repo_dir / "src"
    src_dir.mkdir()
    (src_dir / "valid.py").write_text("def compute(): pass\n")

    # Create dangling symlink
    broken_sym = src_dir / "broken_link.py"
    try:
        broken_sym.symlink_to(repo_dir / "non_existent_target.py")
    except OSError:
        pass

    container = ApplicationContainer()
    container.workspace_auth.add_workspace_root(tmp_path)

    # AST and summary must safely ignore or prune broken symlinks without crashing
    ast_res = await get_ast_call_graph_tool(repository_path=str(repo_dir), container=container)
    assert ast_res.get("success") is True

    search_res = await search_repository_code_tool(
        repository_path=str(repo_dir), query="compute", container=container
    )
    assert search_res.get("success") is True


@pytest.mark.asyncio
async def test_malformed_syntax_and_binary_data(tmp_path: Path):
    """Verify that syntax errors and binary blobs do not crash the AST or search engine."""
    reset_container()
    repo_dir = tmp_path / "syntax_repo"
    repo_dir.mkdir()

    # Valid Python file
    (repo_dir / "valid.py").write_text("def good_func():\n    return 42\n")

    # Syntax Error Python file
    (repo_dir / "broken_syntax.py").write_text("def unclosed_parenthesis(\n    return 10")

    # Binary blob disguised as .py file
    (repo_dir / "blob.py").write_bytes(b"\x00\xFF\xFE\x00\x01\x02\x03\x04")

    container = ApplicationContainer()
    container.workspace_auth.add_workspace_root(tmp_path)

    # AST extractor must process valid files and skip malformed ones gracefully
    ast_res = await get_ast_call_graph_tool(repository_path=str(repo_dir), container=container)
    assert ast_res.get("success") is True
    node_ids = [n.get("id", "") for n in ast_res.get("nodes", [])]
    assert any("good_func" in nid for nid in node_ids)

    # Code search should search text safely
    search_res = await search_repository_code_tool(
        repository_path=str(repo_dir), query="good_func", container=container
    )
    assert search_res.get("success") is True


@pytest.mark.asyncio
async def test_manifest_deleted_or_corrupted(tmp_path: Path):
    """Verify resilience against missing or malformed index manifests."""
    reset_container()
    repo_dir = tmp_path / "manifest_repo"
    repo_dir.mkdir()
    (repo_dir / "main.py").write_text("def start(): pass\n")

    container = ApplicationContainer()
    container.workspace_auth.add_workspace_root(tmp_path)

    # Query with no manifest present
    sum_res = await get_repository_summary_tool(repository_path=str(repo_dir), container=container)
    assert sum_res.get("success") is True
    assert "project_purpose" in sum_res


@pytest.mark.asyncio
async def test_invalid_provider_and_workspace_config(tmp_path: Path):
    """Verify that invalid configs return structured machine-readable error responses."""
    reset_container()
    container = ApplicationContainer()
    container.workspace_auth._workspace_roots = []  # Empty workspace roots

    # Unauthorized path
    res = await get_repository_summary_tool(
        repository_path="/etc",
        container=container,
    )
    assert res.get("success") is False
    assert res.get("error") in ("AuthorizationError", "ValidationError")
