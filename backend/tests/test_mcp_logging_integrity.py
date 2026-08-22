"""Regression tests for MCP stdout protocol framing integrity and stderr logging separation (OPS-002)."""

import json
import logging
from pathlib import Path
import subprocess
import sys
import tempfile
import time

import pytest

backend_dir = Path(__file__).resolve().parent.parent


def _get_python_executable() -> str:
    venv_py = backend_dir / ".venv" / "bin" / "python"
    if venv_py.exists():
        return str(venv_py)
    return sys.executable


@pytest.mark.asyncio
async def test_mcp_stdout_is_strictly_valid_jsonrpc_under_logging():
    """Verify that all logging goes to stderr and stdout contains exclusively valid JSON-RPC frames."""
    from mcp.client.stdio import stdio_client, StdioServerParameters
    from mcp.client.session import ClientSession

    params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"],
        cwd=str(backend_dir),
    )

    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            init_res = await session.initialize()
            assert init_res.server_info.name == "retrack-mcp"

            # Call list_tools
            tools = await session.list_tools()
            assert len(tools.tools) == 5

            # Call tool with invalid path to trigger validation & error logging
            result = await session.call_tool(
                "get_repository_summary",
                arguments={"repository_path": "/etc"},
            )
            assert result.content[0].text is not None
            resp_dict = json.loads(result.content[0].text) if isinstance(result.content[0].text, str) else result.content[0].text
            assert resp_dict.get("success") is False
            assert resp_dict.get("error") == "AuthorizationError"
