"""Phase 8D — Real MCP Client Interoperability & Repeated Session Cycles.

Validates the stdio transport against the official MCP ClientSession, testing
full initialization handshakes, multi-tool invocations, framing cleanliness,
and repeated connection/reconnection lifecycles.
"""

import asyncio
import json
import os
from pathlib import Path
import sys
import time
import pytest
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

backend_dir = Path(__file__).resolve().parent.parent


@pytest.mark.asyncio
async def test_mcp_real_client_session_and_tool_execution():
    """Verify MCP initialization, tool catalog, and execution over stdio."""
    params = StdioServerParameters(
        command=sys.executable,
        args=["mcp_server.py"],
        cwd=str(backend_dir),
        env={**os.environ, "LLM_PROVIDER_BASE_URL": "http://127.0.0.1:1/v1"},
    )

    t0 = time.perf_counter()
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            # 1. Initialize MCP handshake
            init_res = await session.initialize()
            assert init_res.server_info.name == "retrack-mcp"

            # 2. List tools
            tools_res = await session.list_tools()
            tool_names = [t.name for t in tools_res.tools]
            assert "get_agent_context" in tool_names
            assert "get_repository_summary" in tool_names
            assert "get_ast_call_graph" in tool_names
            assert "search_repository_code" in tool_names
            assert "list_indexed_repositories" in tool_names

            # 3. Call tool: list_indexed_repositories
            res_list = await session.call_tool("list_indexed_repositories", arguments={})
            assert len(res_list.content) == 1
            list_data = json.loads(res_list.content[0].text)
            assert list_data.get("success") is True
            assert "repositories" in list_data

            # 4. Call tool with invalid path to verify graceful error return over MCP
            res_err = await session.call_tool(
                "get_repository_summary",
                arguments={"repository_path": "/nonexistent/path/for/test"},
            )
            err_data = json.loads(res_err.content[0].text)
            assert err_data.get("success") is False
            assert err_data.get("error") in ("AuthorizationError", "ValidationError")

    duration = time.perf_counter() - t0
    assert duration < 20.0


@pytest.mark.asyncio
async def test_repeated_mcp_session_reconnect_cycles():
    """Verify 5 repeated connect, initialize, tool-call, disconnect cycles."""
    params = StdioServerParameters(
        command=sys.executable,
        args=["mcp_server.py"],
        cwd=str(backend_dir),
        env={**os.environ, "LLM_PROVIDER_BASE_URL": "http://127.0.0.1:1/v1"},
    )

    for cycle in range(5):
        t_start = time.perf_counter()
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                init_res = await session.initialize()
                assert init_res.server_info.name == "retrack-mcp"

                tools = await session.list_tools()
                assert len(tools.tools) == 5

                # Call list_indexed_repositories
                res = await session.call_tool("list_indexed_repositories", arguments={})
                data = json.loads(res.content[0].text)
                assert data.get("success") is True

        elapsed = time.perf_counter() - t_start
        assert elapsed < 15.0, f"Cycle {cycle} took too long ({elapsed:.2f}s)"
