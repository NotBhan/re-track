"""Phase 8D — Clean Environment Deployment & Realistic Agent Workflow.

Validates that both entry points (`mcp_server.py` and `python -m app.mcp`) function identically,
and tests realistic multi-turn AI coding-agent exploration workflows over stdio.
"""

import json
from pathlib import Path
import subprocess
import sys
import time
import pytest
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

backend_dir = Path(__file__).resolve().parent.parent


def _get_python_executable() -> str:
    venv_py = backend_dir / ".venv" / "bin" / "python"
    if venv_py.exists():
        return str(venv_py)
    return sys.executable


@pytest.mark.asyncio
async def test_launch_via_mcp_server_script():
    """Verify launch via `python mcp_server.py`."""
    params = StdioServerParameters(
        command=_get_python_executable(),
        args=["mcp_server.py"],
        cwd=str(backend_dir),
    )

    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            init_res = await session.initialize()
            assert init_res.server_info.name == "retrack-mcp"
            tools = await session.list_tools()
            assert len(tools.tools) == 5


@pytest.mark.asyncio
async def test_launch_via_module_app_mcp():
    """Verify launch via `python -m app.mcp`."""
    params = StdioServerParameters(
        command=_get_python_executable(),
        args=["-m", "app.mcp"],
        cwd=str(backend_dir),
    )

    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            init_res = await session.initialize()
            assert init_res.server_info.name == "retrack-mcp"
            tools = await session.list_tools()
            assert len(tools.tools) == 5


@pytest.mark.asyncio
async def test_realistic_agent_multi_turn_interaction(tmp_path: Path):
    """Simulate a realistic 7-turn AI coding agent exploration session over stdio."""
    # Create test repository in workspace
    test_repo = tmp_path / "agent_workload_repo"
    test_repo.mkdir(parents=True, exist_ok=True)
    src_dir = test_repo / "backend"
    src_dir.mkdir(exist_ok=True)

    (src_dir / "main.py").write_text(
        "import auth\n\n"
        "def entrypoint():\n"
        "    auth.verify_token('secret')\n"
    )
    (src_dir / "auth.py").write_text(
        "def verify_token(token: str) -> bool:\n"
        "    return token == 'secret'\n"
    )

    params = StdioServerParameters(
        command=_get_python_executable(),
        args=["mcp_server.py"],
        cwd=str(backend_dir),
        env={"RETRACK_WORKSPACE_ROOTS": str(tmp_path)},
    )

    turn_latencies: list[float] = []

    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            # Turn 1: List all repositories
            t0 = time.perf_counter()
            r1 = await session.call_tool("list_indexed_repositories", arguments={})
            turn_latencies.append((time.perf_counter() - t0) * 1000)
            d1 = json.loads(r1.content[0].text)
            assert d1.get("success") is True

            # Turn 2: Get repository architectural summary
            t0 = time.perf_counter()
            r2 = await session.call_tool("get_repository_summary", arguments={"repository_path": str(test_repo)})
            turn_latencies.append((time.perf_counter() - t0) * 1000)
            d2 = json.loads(r2.content[0].text)
            assert d2.get("success") is True
            assert "project_purpose" in d2
            assert "languages" in d2

            # Turn 3: Search for authentication symbols
            t0 = time.perf_counter()
            r3 = await session.call_tool(
                "search_repository_code",
                arguments={"repository_path": str(test_repo), "query": "verify_token", "limit": 5},
            )
            turn_latencies.append((time.perf_counter() - t0) * 1000)
            d3 = json.loads(r3.content[0].text)
            assert d3.get("success") is True

            # Turn 4: Extract deterministic AST call graph
            t0 = time.perf_counter()
            r4 = await session.call_tool("get_ast_call_graph", arguments={"repository_path": str(test_repo)})
            turn_latencies.append((time.perf_counter() - t0) * 1000)
            d4 = json.loads(r4.content[0].text)
            assert d4.get("success") is True
            assert len(d4.get("nodes", [])) >= 2

            # Turn 5: Exploratory invalid call (unauthorized / forbidden system directory)
            t0 = time.perf_counter()
            r5 = await session.call_tool("get_repository_summary", arguments={"repository_path": "/etc"})
            turn_latencies.append((time.perf_counter() - t0) * 1000)
            d5 = json.loads(r5.content[0].text)
            assert d5.get("success") is False
            assert d5.get("error") in ("AuthorizationError", "ValidationError")

            # Turn 6: Context synthesis query (handles gracefully even if local model is cold or offline)
            t0 = time.perf_counter()
            r6 = await session.call_tool(
                "get_agent_context",
                arguments={
                    "task_prompt": "Fix token validation bug in auth.py",
                    "repository_path": str(test_repo),
                    "max_tokens": 4000,
                },
            )
            turn_latencies.append((time.perf_counter() - t0) * 1000)
            d6 = json.loads(r6.content[0].text)
            # Response is either successful synthesis or graceful handled error
            assert "success" in d6

            # Turn 7: Valid post-error follow-up call
            t0 = time.perf_counter()
            r7 = await session.call_tool(
                "search_repository_code",
                arguments={"repository_path": str(test_repo), "query": "entrypoint"},
            )
            turn_latencies.append((time.perf_counter() - t0) * 1000)
            d7 = json.loads(r7.content[0].text)
            assert d7.get("success") is True

    # Validate latency bounds for deterministic turns (Turns 1, 2, 3, 4, 5, 7)
    det_latencies = [turn_latencies[0], turn_latencies[1], turn_latencies[2], turn_latencies[3], turn_latencies[4], turn_latencies[6]]
    det_latencies.sort()
    p50 = det_latencies[int(len(det_latencies) * 0.5)]
    p95 = det_latencies[int(len(det_latencies) * 0.95)]
    assert p50 < 100.0, f"P50 latency exceeded budget: {p50:.2f}ms"
    assert p95 < 500.0, f"P95 latency exceeded budget: {p95:.2f}ms"
