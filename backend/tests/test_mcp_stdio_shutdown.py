"""Regression tests for MCP Stdio process lifecycle and graceful shutdown (OPS-003)."""

import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

import pytest

backend_dir = Path(__file__).resolve().parent.parent


def _get_python_executable() -> str:
    # Prefer virtualenv python if available
    venv_py = backend_dir / ".venv" / "bin" / "python"
    if venv_py.exists():
        return str(venv_py)
    return sys.executable


@pytest.mark.asyncio
async def test_mcp_process_terminates_on_stdin_eof():
    """Verify that a real MCP server process terminates promptly and cleanly when client closes stdio session."""
    from mcp.client.stdio import stdio_client, StdioServerParameters
    from mcp.client.session import ClientSession

    params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"],
        cwd=str(backend_dir),
    )

    t0 = time.perf_counter()
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            init_res = await session.initialize()
            assert init_res.server_info.name == "retrack-mcp"
            tools = await session.list_tools()
            assert len(tools.tools) == 5

    # Context manager has exited, meaning stdio streams closed (EOF)
    elapsed = time.perf_counter() - t0
    assert elapsed < 15.0


def test_mcp_process_handles_sigint():
    """Verify clean exit upon receiving SIGINT."""
    py_exec = _get_python_executable()
    mcp_script = backend_dir / "mcp_server.py"

    proc = subprocess.Popen(
        [py_exec, str(mcp_script)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(backend_dir),
    )

    time.sleep(0.5)
    t0 = time.perf_counter()
    proc.send_signal(signal.SIGINT)
    proc.wait(timeout=2.5)
    elapsed = time.perf_counter() - t0

    assert proc.returncode in (0, -signal.SIGINT, 130)
    assert elapsed < 2.0


def test_mcp_process_handles_sigterm():
    """Verify clean exit upon receiving SIGTERM."""
    py_exec = _get_python_executable()
    mcp_script = backend_dir / "mcp_server.py"

    proc = subprocess.Popen(
        [py_exec, str(mcp_script)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(backend_dir),
    )

    time.sleep(0.5)
    t0 = time.perf_counter()
    proc.send_signal(signal.SIGTERM)
    proc.wait(timeout=2.5)
    elapsed = time.perf_counter() - t0

    assert proc.returncode in (0, -signal.SIGTERM, 143)
    assert elapsed < 2.0
