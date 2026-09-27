"""MCP production-contract audit suite.

Covers the current MCP boundary against the current application contracts:

* workspace authorization and path/symlink containment at the tool boundary
* fail-closed behavior when workspace authorization is unavailable
* AST/search truthfulness on malformed, binary, unreadable, and empty repositories
* repository-list freshness for cross-process registrations
* concurrency-slot release when an in-flight context request is cancelled
* real stdio protocol handling of malformed JSON-RPC, unknown tools, invalid
  arguments, repeated invocations, resources, and EOF shutdown
* real stdio regression coverage for ``get_agent_context`` (services initialized)
"""

import asyncio
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time
from typing import Any, List, Optional
from unittest.mock import MagicMock

import psutil
import pytest

from app.application.container import ApplicationContainer
from app.application.domain.repository import IndexedRepositoryRecord
from app.application.ports.repository_metadata import RepositoryMetadataPort
from app.mcp.tools import (
    get_agent_context_tool,
    get_ast_call_graph_tool,
    get_repository_summary_tool,
    list_indexed_repositories_tool,
    search_repository_code_tool,
)
from app.services.repository_manager import RepositoryManager
from app.services.workspace_authorization_service import WorkspaceAuthorizationService

backend_dir = Path(__file__).resolve().parent.parent


class InMemoryMetaStore(RepositoryMetadataPort):
    """Minimal metadata port backed by an in-memory dict."""

    def __init__(self, records: Optional[List[IndexedRepositoryRecord]] = None) -> None:
        self._records = {r.id: r for r in (records or [])}

    def load_all(self) -> List[IndexedRepositoryRecord]:
        return list(self._records.values())

    def get_by_id(self, repo_id: str) -> Optional[IndexedRepositoryRecord]:
        return self._records.get(repo_id)

    def get_by_path(self, path: str) -> Optional[IndexedRepositoryRecord]:
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


def _build_container(root: Path, *, authorize: bool = True) -> ApplicationContainer:
    container = ApplicationContainer.create()
    store = InMemoryMetaStore()
    container.metadata_store = store
    container.workspace_auth = (
        WorkspaceAuthorizationService(metadata_store=store, workspace_roots=[root])
        if authorize
        else None
    )
    return container


def _backend_python() -> str:
    venv_py = backend_dir / ".venv" / "bin" / "python"
    return str(venv_py) if venv_py.exists() else sys.executable


def _subprocess_env(home: Path, workspace_root: Path) -> dict[str, str]:
    """Hermetic environment: isolated HOME and a dead provider endpoint (fast refusal)."""
    return {
        **os.environ,
        "HOME": str(home),
        "RETRACK_WORKSPACE_ROOTS": str(workspace_root),
        "LLM_ENDPOINT": "http://127.0.0.1:1/v1",
    }


def _read_json_line(proc: subprocess.Popen, timeout: float = 90.0) -> dict[str, Any]:
    sel = selectors.DefaultSelector()
    sel.register(proc.stdout, selectors.EVENT_READ)
    try:
        if not sel.select(timeout):
            raise TimeoutError("no MCP response within timeout")
        line = proc.stdout.readline()
        if not line:
            raise EOFError("MCP server closed stdout")
        return json.loads(line.decode("utf-8"))
    finally:
        sel.close()


def _send(proc: subprocess.Popen, payload: dict[str, Any]) -> None:
    proc.stdin.write((json.dumps(payload) + "\n").encode("utf-8"))
    proc.stdin.flush()


def _raw_call(proc: subprocess.Popen, request_id: int, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    _send(
        proc,
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        },
    )
    return _read_json_line(proc)


# ---------------------------------------------------------------------------
# Authorization boundary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tool_boundary_rejects_unauthorized_paths(tmp_path: Path):
    """Registered-root containment: sibling prefixes, traversal, symlinks, root, home."""
    root = tmp_path / "authorized"
    root.mkdir()
    repo = root / "repo"
    repo.mkdir()
    (repo / "main.py").write_text("def run():\n    return 1\n", encoding="utf-8")

    outside = tmp_path / "outside"
    outside.mkdir()
    evil_sibling = tmp_path / "authorized-evil"
    evil_sibling.mkdir()

    escape = root / "escape"
    escape.symlink_to(outside, target_is_directory=True)

    container = _build_container(root)

    rejected = [
        (str(outside), "AuthorizationError"),
        (str(evil_sibling), "AuthorizationError"),
        (str(escape), "AuthorizationError"),
        (str(root / "repo" / ".." / ".." / "outside"), "AuthorizationError"),
        ("/", "ValidationError"),
        ("/tmp", "AuthorizationError"),
        (str(Path.home()), "AuthorizationError"),
        (str(root / "missing-repo"), "ValidationError"),
    ]
    for path, expected_error in rejected:
        result = await get_repository_summary_tool(path, container=container)
        assert result["success"] is False, (path, result)
        assert result["error"] == expected_error, (path, result)
        assert "context_markdown" not in result

    accepted = await get_repository_summary_tool(str(repo), container=container)
    assert accepted["success"] is True, accepted


@pytest.mark.asyncio
async def test_tool_boundary_fails_closed_without_authorization(tmp_path: Path):
    """A container without a workspace-authorization port must deny, not allow."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "main.py").write_text("def run():\n    return 1\n", encoding="utf-8")

    container = _build_container(tmp_path, authorize=False)
    assert container.workspace_auth is None

    for tool_call in (
        lambda: get_repository_summary_tool(str(repo), container=container),
        lambda: get_ast_call_graph_tool(str(repo), container=container),
        lambda: search_repository_code_tool(str(repo), "run", container=container),
        lambda: get_agent_context_tool("trace run", str(repo), container=container),
    ):
        result = await tool_call()
        assert result["success"] is False, result
        assert result["error"] == "AuthorizationError", result


# ---------------------------------------------------------------------------
# Tool truthfulness
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ast_graph_nodes_and_edges_are_real(tmp_path: Path):
    """Every node must reference a real file/line and every edge a real node."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.py").write_text(
        "class Service:\n"
        "    def run(self):\n"
        "        return helper()\n\n"
        "def helper():\n"
        "    return 1\n",
        encoding="utf-8",
    )
    (repo / "b.py").write_text("def caller():\n    return helper()\n", encoding="utf-8")
    (repo / "malformed.py").write_text("def broken(:\n    pass\n", encoding="utf-8")
    (repo / "notes.txt").write_text("not source code", encoding="utf-8")

    container = _build_container(tmp_path)
    result = await get_ast_call_graph_tool(str(repo), container=container)

    assert result["success"] is True, result
    assert result["call_graph_status"] in ("analyzed", "zero_edges", "not_analyzed", "failed")
    node_ids = {node["id"] for node in result["nodes"]}
    for node in result["nodes"]:
        node_path = Path(node["file"])
        resolved = node_path if node_path.is_absolute() else repo / node_path
        assert resolved.exists(), node
        assert node["line"] >= 1, node
        assert node["kind"], node
    for edge in result["edges"]:
        assert edge["source"] in node_ids, edge
        assert edge["target"] in node_ids, edge
        assert edge["kind"], edge


@pytest.mark.asyncio
async def test_ast_graph_unavailable_state_is_not_fabricated(tmp_path: Path):
    """A repository with no analyzable source reports an empty, explicitly-unsupported graph."""
    repo = tmp_path / "empty_repo"
    repo.mkdir()
    (repo / "README.md").write_text("documentation only", encoding="utf-8")

    container = _build_container(tmp_path)
    result = await get_ast_call_graph_tool(str(repo), container=container)

    assert result["success"] is True, result
    assert result["nodes"] == []
    assert result["edges"] == []
    assert result["call_graph_status"] in ("not_analyzed", "zero_edges")


@pytest.mark.asyncio
async def test_search_confines_to_repository_and_survives_bad_files(tmp_path: Path):
    """Search returns repository-relative paths only; symlink escapes never leak."""
    root = tmp_path / "authorized"
    root.mkdir()
    repo = root / "repo"
    repo.mkdir()
    (repo / "good.py").write_text("def needle_symbol():\n    return 1\n", encoding="utf-8")
    (repo / "binaryish.py").write_bytes(b"def needle_symbol():\n" + b"\x00\xff" * 64)
    (repo / "malformed.py").write_text("def broken(:\n\x00\x01", encoding="utf-8")

    unreadable = repo / "unreadable.py"
    unreadable.write_text("def needle_symbol():\n    return 2\n", encoding="utf-8")
    unreadable.chmod(0o000)

    secrets_dir = tmp_path / "secrets"
    secrets_dir.mkdir()
    (secrets_dir / "outside.py").write_text("def needle_symbol():\n    return 'outside'\n", encoding="utf-8")
    (repo / "escape.py").symlink_to(secrets_dir / "outside.py")

    container = _build_container(root)
    result = await search_repository_code_tool(str(repo), "needle_symbol", container=container)

    assert result["success"] is True, result
    paths = [item["file_path"] for item in result["results"]]
    assert any(path.endswith("good.py") for path in paths), paths
    assert not any("escape" in path for path in paths), paths
    assert all(not os.path.isabs(path) for path in paths), paths
    assert all("outside" not in item["snippet"] for item in result["results"]), result["results"]


@pytest.mark.asyncio
async def test_list_repositories_reflects_cross_process_registrations(tmp_path: Path):
    """A registration persisted by another process appears without an MCP restart."""
    store_path = tmp_path / "repositories.json"
    repo = tmp_path / "repo"
    repo.mkdir()

    container = ApplicationContainer.create()
    container.repository_manager = RepositoryManager(store_path=store_path)
    container.workspace_auth = WorkspaceAuthorizationService(
        metadata_store=InMemoryMetaStore(), workspace_roots=[tmp_path]
    )

    store_path.write_text(
        json.dumps(
            {
                "external-id": {
                    "id": "external-id",
                    "name": "External Repo",
                    "source_type": "local",
                    "local_path": str(repo),
                    "branch": "feature/x",
                    "commit_hash": "deadbeef",
                    "status": "indexed",
                    "languages": ["Python"],
                    "frameworks": [],
                    "file_count": 3,
                    "size_bytes": 42,
                    "indexed_at": "2026-01-01T00:00:00Z",
                    "summary": "external summary",
                    "entry_points": [],
                    "architecture": "flat",
                    "components": [],
                    "dependencies": [],
                    "metadata": {},
                    "created_at": "2026-01-01T00:00:00Z",
                }
            }
        ),
        encoding="utf-8",
    )

    # The long-lived manager had loaded before the external write.
    assert container.repository_manager.list_repositories() == []

    result = await list_indexed_repositories_tool(container=container)

    assert result["success"] is True, result
    assert result["total_count"] == 1
    entry = result["repositories"][0]
    assert entry["id"] == "external-id"
    assert entry["branch"] == "feature/x"
    assert entry["commit_hash"] == "deadbeef"
    assert entry["size_bytes"] == 42
    assert entry["call_graph_status"] == "not_analyzed"


# ---------------------------------------------------------------------------
# Concurrency lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_context_slot_released_when_request_is_cancelled(tmp_path: Path):
    """A cancelled (disconnected) context request must not strand the single slot."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "main.py").write_text("def run():\n    return 1\n", encoding="utf-8")

    container = _build_container(tmp_path)
    container.cognee_service = MagicMock()
    container.indexing_service = MagicMock()
    container.indexing_service.discover_files.return_value = [repo / "main.py"]
    container.indexing_service.filter_files.return_value = [repo / "main.py"]

    started = asyncio.Event()

    class BlockingContextService:
        async def generate_context_package(self, *args, **kwargs):
            started.set()
            await asyncio.Event().wait()

    container.context_service = BlockingContextService()

    task = asyncio.create_task(
        get_agent_context_tool("blocked task", str(repo), container=container)
    )
    await asyncio.wait_for(started.wait(), timeout=10.0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert container.concurrency_guard.waiting_count == 0

    class WorkingContextService:
        async def generate_context_package(self, *args, **kwargs):
            package = MagicMock()
            package.markdown = "# Recovered Context"
            return package

    container.context_service = WorkingContextService()
    result = await get_agent_context_tool("recovered task", str(repo), container=container)
    assert result["success"] is True, result
    assert isinstance(result["context_markdown"], str)
    assert result["context_markdown"]


# ---------------------------------------------------------------------------
# Real subprocess: raw protocol, resources, lifecycle
# ---------------------------------------------------------------------------


def test_real_stdio_protocol_rejections_resources_and_eof(tmp_path: Path):
    """Raw JSON-RPC session: malformed input, rejects, repeated calls, resources, EOF exit."""
    home = tmp_path / "home"
    home.mkdir()
    root = tmp_path / "workspace"
    root.mkdir()
    repo = root / "repo"
    repo.mkdir()
    (repo / "main.py").write_text("def run():\n    return 1\n", encoding="utf-8")

    proc = subprocess.Popen(
        [_backend_python(), "mcp_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(backend_dir),
        env=_subprocess_env(home, root),
    )
    child = psutil.Process(proc.pid)
    try:
        # 1. Malformed JSON must not corrupt stdout or kill the process.
        proc.stdin.write(b"this is not json\n")
        proc.stdin.flush()

        _send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "production-contract-test", "version": "0.1"},
                },
            },
        )
        init = _read_json_line(proc, timeout=120.0)
        assert init.get("id") == 1
        server_info = init["result"].get("serverInfo") or init["result"].get("server_info") or {}
        assert server_info.get("name") == "retrack-mcp"

        _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})

        # 2. Unknown tool and invalid argument type are structured rejections.
        unknown = _raw_call(proc, 2, "no_such_tool", {})
        assert unknown["result"]["isError"] is True
        bad_args = _raw_call(proc, 3, "get_repository_summary", {"repository_path": 12345})
        assert bad_args["result"]["isError"] is True

        # 3. Repeated well-formed invocations stay successful and framed.
        baseline = {
            "rss": child.memory_info().rss,
            "fds": child.num_fds(),
            "threads": child.num_threads(),
        }
        latencies: list[float] = []
        request_id = 10
        for _ in range(3):
            for tool, arguments in (
                ("list_indexed_repositories", {}),
                ("get_repository_summary", {"repository_path": str(repo)}),
                ("get_ast_call_graph", {"repository_path": str(repo)}),
                ("search_repository_code", {"repository_path": str(repo), "query": "run"}),
            ):
                t0 = time.perf_counter()
                response = _raw_call(proc, request_id, tool, arguments)
                latencies.append((time.perf_counter() - t0) * 1000)
                request_id += 1
                assert "result" in response, response
                assert response["result"].get("isError") is not True, (tool, response)
                payload = json.loads(response["result"]["content"][0]["text"])
                assert payload.get("success") is True, (tool, payload)

        after = {
            "rss": child.memory_info().rss,
            "fds": child.num_fds(),
            "threads": child.num_threads(),
        }
        rss_delta_mb = (after["rss"] - baseline["rss"]) / (1024 * 1024)
        assert rss_delta_mb < 200.0, f"RSS grew by {rss_delta_mb:.1f} MB"
        assert after["fds"] - baseline["fds"] < 30
        assert after["threads"] - baseline["threads"] < 20

        latencies.sort()
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[int(len(latencies) * 0.95) - 1]
        assert p95 < 5000.0, f"deterministic tool p95 too slow: {p95:.1f}ms"
        print(
            f"\n[MCP raw stdio] {len(latencies)} calls | p50={p50:.1f}ms | p95={p95:.1f}ms | "
            f"RSS delta={rss_delta_mb:.1f}MB | fd delta={after['fds'] - baseline['fds']} | "
            f"thread delta={after['threads'] - baseline['threads']}"
        )

        # 4. EOF terminates cleanly with no orphaned children.
        proc.stdin.close()
        proc.wait(timeout=30.0)
        assert proc.returncode == 0, proc.returncode
        try:
            orphans = child.children(recursive=True)
        except psutil.NoSuchProcess:
            orphans = []
        assert orphans == []
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()


@pytest.mark.asyncio
async def test_real_stdio_get_agent_context_is_service_initialized(tmp_path: Path):
    """Regression: get_agent_context must reach the real pipeline, not 'not initialized'."""
    from mcp.client.session import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    home = tmp_path / "home"
    home.mkdir()
    root = tmp_path / "workspace"
    root.mkdir()
    repo = root / "repo"
    repo.mkdir()
    (repo / "auth.py").write_text(
        "def authenticate(user):\n    return verify(user)\n\n\n"
        "def verify(user):\n    return bool(user)\n",
        encoding="utf-8",
    )

    params = StdioServerParameters(
        command=_backend_python(),
        args=["mcp_server.py"],
        cwd=str(backend_dir),
        env=_subprocess_env(home, root),
    )

    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(
                "get_agent_context",
                {
                    "task_prompt": "Explain how authenticate verifies a user",
                    "repository_path": str(repo),
                    "max_tokens": 2000,
                },
            )
            assert getattr(result, "is_error", False) is not True
            payload = json.loads(result.content[0].text)

    assert payload.get("success") is True, payload
    assert payload.get("error") != "CogneeServiceError", payload
    assert "Backend services not initialized" not in json.dumps(payload)
    assert isinstance(payload.get("context_markdown"), str)
    assert payload.get("evidence_state") in ("sufficient", "partial", "insufficient", "none")
    assert "compaction" in payload
    assert "quantization_warning" in payload
    if payload.get("abstained"):
        assert payload.get("model_claims_allowed") is False
        assert payload.get("model_invoked") is False
        assert payload.get("abstention_reason")
    print(
        f"\n[MCP get_agent_context] evidence_state={payload.get('evidence_state')} "
        f"abstained={payload.get('abstained')} model_invoked={payload.get('model_invoked')} "
        f"inference_status={payload.get('inference_status')} "
        f"total_time_ms={payload.get('total_time_ms')}"
    )
