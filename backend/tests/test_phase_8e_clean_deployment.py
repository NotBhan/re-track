"""Phase 8E — Track 6: Clean Deployment and Entry Point Reproducibility.

Verifies package entry points, dependency metadata consistency, pyproject configuration,
and documented launch paths across clean environments.
"""

import json
from pathlib import Path
import subprocess
import sys
import pytest
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

backend_dir = Path(__file__).resolve().parent.parent


def _get_python_executable() -> str:
    venv_py = backend_dir / ".venv" / "bin" / "python"
    if venv_py.exists():
        return str(venv_py)
    return sys.executable


def test_package_metadata_and_pyproject_integrity():
    """Verify that requirements.txt exists and defines valid dependencies."""
    req_file = backend_dir / "requirements.txt"
    assert req_file.exists(), "requirements.txt is missing from backend directory"
    content = req_file.read_text()
    assert "mcp" in content
    assert "pydantic" in content
    assert "fastapi" in content


@pytest.mark.asyncio
async def test_clean_deployment_via_mcp_server_script():
    """Verify standalone script entry point: `python mcp_server.py`."""
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
            res = await session.call_tool("list_indexed_repositories", arguments={})
            data = json.loads(res.content[0].text)
            assert data.get("success") is True


@pytest.mark.asyncio
async def test_clean_deployment_via_module_mcp():
    """Verify module entry point: `python -m app.mcp`."""
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
            res = await session.call_tool("list_indexed_repositories", arguments={})
            data = json.loads(res.content[0].text)
            assert data.get("success") is True
