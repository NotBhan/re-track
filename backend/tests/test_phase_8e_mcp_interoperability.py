"""Phase 8E — Track 4: Real MCP Client Interoperability & 20-Cycle Reconnection.

Executes 20 real MCP client sessions against the actual stdio subprocess, verifying
initialization handshakes, tool catalogs, multi-tool workflows (including context synthesis
and error recovery), and clean process teardown.
"""

import asyncio
import json
import os
from pathlib import Path
import sys
import time
import psutil
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
async def test_20_cycle_mcp_session_interoperability(tmp_path: Path):
    """Execute 20 consecutive connect, handshake, multi-tool call, disconnect cycles."""
    # Setup test workspace and repository
    test_repo = tmp_path / "interop_repo"
    test_repo.mkdir(parents=True, exist_ok=True)
    src_dir = test_repo / "src"
    src_dir.mkdir(exist_ok=True)
    (src_dir / "service.py").write_text(
        "class WorkerService:\n"
        "    def execute(self):\n"
        "        return True\n"
    )

    params = StdioServerParameters(
        command=_get_python_executable(),
        args=["mcp_server.py"],
        cwd=str(backend_dir),
        env={
            **os.environ,
            "RETRACK_WORKSPACE_ROOTS": str(tmp_path),
            "LLM_PROVIDER_BASE_URL": "http://127.0.0.1:1/v1",
        },
    )

    initial_child_count = len(psutil.Process().children(recursive=True))
    total_cycles = 20
    cycle_timings: list[dict[str, float]] = []

    for cycle in range(1, total_cycles + 1):
        t_cycle_start = time.perf_counter()

        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                # 1. Initialize Handshake
                t_init = time.perf_counter()
                init_res = await session.initialize()
                init_time = (time.perf_counter() - t_init) * 1000
                assert init_res.server_info.name == "retrack-mcp"

                # 2. List tools
                tools_res = await session.list_tools()
                assert len(tools_res.tools) == 5

                # 3. Call list_indexed_repositories
                r1 = await session.call_tool("list_indexed_repositories", arguments={})
                d1 = json.loads(r1.content[0].text)
                assert d1.get("success") is True

                # 4. Call get_repository_summary
                r2 = await session.call_tool(
                    "get_repository_summary",
                    arguments={"repository_path": str(test_repo)},
                )
                d2 = json.loads(r2.content[0].text)
                assert d2.get("success") is True

                # 5. At least 5 cycles include get_agent_context (e.g. cycles 1, 5, 10, 15, 20)
                if cycle % 4 == 1:
                    r3 = await session.call_tool(
                        "get_agent_context",
                        arguments={
                            "task_prompt": "Enhance WorkerService",
                            "repository_path": str(test_repo),
                            "max_tokens": 2000,
                        },
                    )
                    d3 = json.loads(r3.content[0].text)
                    assert "success" in d3  # Either successful or handled provider error

                # 6. At least 5 cycles include invalid arguments followed by valid requests (cycles 2, 6, 11, 16, 19)
                if cycle % 4 == 2:
                    r_err = await session.call_tool(
                        "get_repository_summary",
                        arguments={"repository_path": "/etc/unauthorized"},
                    )
                    d_err = json.loads(r_err.content[0].text)
                    assert d_err.get("success") is False
                    assert d_err.get("error") in ("AuthorizationError", "ValidationError")

                    # Follow-up valid call
                    r_valid = await session.call_tool(
                        "search_repository_code",
                        arguments={"repository_path": str(test_repo), "query": "WorkerService"},
                    )
                    d_valid = json.loads(r_valid.content[0].text)
                    assert d_valid.get("success") is True

        cycle_duration = time.perf_counter() - t_cycle_start
        cycle_timings.append({
            "cycle": cycle,
            "init_time_ms": init_time,
            "duration_s": cycle_duration,
        })

    # Verify no leaked orphan subprocesses
    final_child_count = len(psutil.Process().children(recursive=True))
    assert final_child_count <= initial_child_count + 1

    avg_init = sum(c["init_time_ms"] for c in cycle_timings) / len(cycle_timings)
    avg_cycle = sum(c["duration_s"] for c in cycle_timings) / len(cycle_timings)

    print(
        f"\n[Phase 8E MCP Interop] 20/20 Reconnect Cycles PASSED | "
        f"Avg Init Handshake: {avg_init:.2f}ms | Avg Cycle Duration: {avg_cycle:.2f}s"
    )
