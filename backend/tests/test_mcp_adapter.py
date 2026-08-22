"""Tests for RE:Track Model Context Protocol (MCP) Adapter.

Validates:
1. MCP tool registration and schema contracts.
2. Architectural boundary purity (inbound adapter only imports use cases, DTOs, container).
3. Tool execution (get_agent_context, get_repository_summary, get_ast_call_graph, search_repository_code, list_indexed_repositories).
4. Error handling and path validation / security boundaries.
5. Concurrency safety.
6. Real MCP JSON-RPC protocol communication via ClientSession and memory streams.
"""

import ast
import asyncio
from pathlib import Path
from typing import Any, Optional
import pytest
import anyio

from mcp.client.session import ClientSession
from mcp.shared.memory import create_client_server_memory_streams

from app.application.container import ApplicationContainer
from app.mcp.server import create_mcp_server
from app.mcp import tools as mcp_tools


@pytest.fixture
def test_repo_dir(tmp_path: Path) -> Path:
    """Create a realistic temporary repository for testing."""
    repo = tmp_path / "sample_repo"
    repo.mkdir()

    src = repo / "src"
    src.mkdir()

    # Create Python module
    auth_py = src / "auth.py"
    auth_py.write_text(
        "class AuthService:\n"
        "    def authenticate(self, user: str) -> bool:\n"
        "        return user == 'admin'\n"
    )

    models_py = src / "models.py"
    models_py.write_text(
        "class User:\n"
        "    def __init__(self, username: str):\n"
        "        self.username = username\n"
    )

    server_py = src / "server.py"
    server_py.write_text(
        "from src.auth import AuthService\n"
        "from src.models import User\n"
        "def main():\n"
        "    auth = AuthService()\n"
        "    user = User('alice')\n"
        "    auth.authenticate(user.username)\n"
    )

    # Manifest directory
    retrack_dir = repo / ".retrack"
    retrack_dir.mkdir()
    manifest = retrack_dir / "manifest.json"
    manifest.write_text('{"version": "1.0.0", "files": ["src/auth.py", "src/models.py", "src/server.py"]}')

    return repo


async def get_test_container(workspace_root: Optional[Path] = None) -> ApplicationContainer:
    """Construct and initialize an ApplicationContainer for testing."""
    c = ApplicationContainer.create()
    try:
        await c.initialize()
    except Exception:
        pass
    if workspace_root and hasattr(c, "workspace_auth") and c.workspace_auth:
        c.workspace_auth.add_workspace_root(workspace_root)
    return c


@pytest.mark.asyncio
async def test_mcp_tool_registration():
    """Verify all 5 MVP tools are registered on the MCPServer instance with proper descriptions."""
    server = create_mcp_server()
    tools = await server.list_tools()
    tool_names = {t.name for t in tools}

    expected_tools = {
        "get_agent_context",
        "get_repository_summary",
        "get_ast_call_graph",
        "search_repository_code",
        "list_indexed_repositories",
    }

    assert expected_tools.issubset(tool_names), f"Missing tools: {expected_tools - tool_names}"

    for tool in tools:
        assert tool.description, f"Tool {tool.name} missing description"
        assert tool.input_schema, f"Tool {tool.name} missing input schema"
        assert tool.input_schema.get("type") == "object"


@pytest.mark.asyncio
async def test_mcp_schema_validation():
    """Verify input schemas for all 5 tools contain required/optional properties and correct types."""
    server = create_mcp_server()
    tools = await server.list_tools()
    tools_by_name = {t.name: t for t in tools}

    # 1. get_agent_context
    ctx_schema = tools_by_name["get_agent_context"].input_schema
    props = ctx_schema["properties"]
    assert "task_prompt" in props
    assert "repository_path" in props
    assert "max_tokens" in props
    assert "include_structural_graph" in props
    assert ctx_schema["required"] == ["task_prompt", "repository_path"]

    # 2. get_repository_summary
    sum_schema = tools_by_name["get_repository_summary"].input_schema
    assert sum_schema["properties"]["repository_path"]["type"] == "string"
    assert sum_schema["required"] == ["repository_path"]

    # 3. get_ast_call_graph
    ast_schema = tools_by_name["get_ast_call_graph"].input_schema
    assert "repository_path" in ast_schema["properties"]
    assert "file_filter" in ast_schema["properties"]
    assert "max_nodes" in ast_schema["properties"]
    assert ast_schema["required"] == ["repository_path"]

    # 4. search_repository_code
    search_schema = tools_by_name["search_repository_code"].input_schema
    assert "repository_path" in search_schema["properties"]
    assert "query" in search_schema["properties"]
    assert search_schema["required"] == ["repository_path", "query"]

    # 5. list_indexed_repositories
    list_schema = tools_by_name["list_indexed_repositories"].input_schema
    assert list_schema["type"] == "object"


def test_mcp_architectural_boundary_purity():
    """Verify app/mcp/ contains ZERO direct imports of low-level databases, Cognee, or concrete services."""
    mcp_dir = Path(__file__).parent.parent / "app" / "mcp"
    py_files = list(mcp_dir.glob("*.py"))
    assert py_files, "No python files found in app/mcp"

    forbidden_modules = {
        "cognee",
        "sqlalchemy",
        "lancedb",
        "kuzu",
        "falkordb",
        "app.services.cognee_service",
        "app.services.indexing_service",
        "app.services.context_service",
        "app.services.repository_summary",
        "app.services.source_search_service",
    }

    for py_file in py_files:
        content = py_file.read_text()
        tree = ast.parse(content, filename=str(py_file))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for forbidden in forbidden_modules:
                        assert not alias.name.startswith(forbidden), (
                            f"Violation in {py_file.name}: Direct import of {alias.name}"
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for forbidden in forbidden_modules:
                        assert not node.module.startswith(forbidden), (
                            f"Violation in {py_file.name}: Direct from-import of {node.module}"
                        )


@pytest.mark.asyncio
async def test_mcp_get_agent_context_success(test_repo_dir: Path):
    """Verify get_agent_context tool execution produces valid Markdown and symbol metadata."""
    container = await get_test_container(test_repo_dir)
    res = await mcp_tools.get_agent_context_tool(
        task_prompt="How does AuthService authenticate users?",
        repository_path=str(test_repo_dir),
        max_tokens=4000,
        container=container,
    )

    assert res["success"] is True, f"Failed: {res}"
    assert "context_markdown" in res
    assert len(res["context_markdown"]) > 0
    assert "task_summary" in res
    assert "AuthService" in str(res["extracted_symbols"]) or "AuthService" in res["context_markdown"]
    assert isinstance(res["total_time_ms"], int)


@pytest.mark.asyncio
async def test_mcp_get_repository_summary_success(test_repo_dir: Path):
    """Verify get_repository_summary tool returns accurate languages, components, and purpose."""
    container = await get_test_container(test_repo_dir)
    res = await mcp_tools.get_repository_summary_tool(
        repository_path=str(test_repo_dir),
        container=container,
    )

    assert res["success"] is True, f"Failed: {res}"
    assert res["repository_path"] == str(test_repo_dir)
    assert "Python" in res["languages"]
    assert res["file_count"] >= 3
    assert isinstance(res["key_components"], list)
    assert isinstance(res["entry_points"], list)


@pytest.mark.asyncio
async def test_mcp_get_ast_call_graph_success(test_repo_dir: Path):
    """Verify get_ast_call_graph tool returns nodes, edges, and respects filtering/max_nodes."""
    container = await get_test_container(test_repo_dir)
    res = await mcp_tools.get_ast_call_graph_tool(
        repository_path=str(test_repo_dir),
        max_nodes=100,
        container=container,
    )

    assert res["success"] is True, f"Failed: {res}"
    assert res["total_nodes"] > 0
    assert isinstance(res["nodes"], list)
    assert isinstance(res["edges"], list)

    labels = {n["label"] for n in res["nodes"]}
    assert any("AuthService" in l or "authenticate" in l or "User" in l for l in labels)

    # Test file_filter
    filter_res = await mcp_tools.get_ast_call_graph_tool(
        repository_path=str(test_repo_dir),
        file_filter="src/auth.py",
        container=container,
    )
    assert filter_res["success"] is True
    for n in filter_res["nodes"]:
        assert "auth.py" in n["file"]


@pytest.mark.asyncio
async def test_mcp_search_repository_code_success(test_repo_dir: Path):
    """Verify search_repository_code tool returns ranked candidates with matched symbols and snippets."""
    container = await get_test_container(test_repo_dir)
    res = await mcp_tools.search_repository_code_tool(
        repository_path=str(test_repo_dir),
        query="AuthService authenticate",
        limit=5,
        container=container,
    )

    assert res["success"] is True, f"Failed: {res}"
    assert res["total_results"] > 0
    assert len(res["results"]) > 0

    first = res["results"][0]
    assert "auth.py" in first["file_path"] or "server.py" in first["file_path"]
    assert first["score"] > 0
    assert "AuthService" in str(first["matched_symbols"]) or "authenticate" in str(first["matched_symbols"])


@pytest.mark.asyncio
async def test_mcp_list_indexed_repositories_success():
    """Verify list_indexed_repositories tool executes and returns repository listing."""
    container = await get_test_container()
    res = await mcp_tools.list_indexed_repositories_tool(container=container)
    assert res["success"] is True
    assert isinstance(res["repositories"], list)
    assert "total_count" in res


@pytest.mark.asyncio
async def test_mcp_invalid_repository_path_error():
    """Verify supplying non-existent or invalid repository paths returns clean validation errors."""
    container = await get_test_container()
    res = await mcp_tools.get_agent_context_tool(
        task_prompt="Find bug",
        repository_path="/non/existent/path/that/does/not/exist/12345",
        container=container,
    )
    assert res["success"] is False
    assert res["error"] == "ValidationError"
    assert "does not exist" in res["message"]


@pytest.mark.asyncio
async def test_mcp_path_traversal_and_root_security(tmp_path: Path):
    """Verify scanning root directory or empty path is prohibited."""
    container = await get_test_container()
    # Root access check
    root_res = await mcp_tools.get_repository_summary_tool(
        repository_path="/",
        container=container,
    )
    assert root_res["success"] is False
    assert root_res["error"] == "ValidationError"
    assert "prohibited" in root_res["message"].lower() or "restricted" in root_res["message"].lower()

    # Empty path check
    empty_res = await mcp_tools.get_ast_call_graph_tool(
        repository_path="",
        container=container,
    )
    assert empty_res["success"] is False
    assert empty_res["error"] == "ValidationError"


@pytest.mark.asyncio
async def test_mcp_concurrent_tool_invocations(test_repo_dir: Path):
    """Verify concurrent read-only tool calls execute safely without deadlock."""
    container = await get_test_container(test_repo_dir)
    coros = [
        mcp_tools.get_repository_summary_tool(str(test_repo_dir), container=container),
        mcp_tools.get_ast_call_graph_tool(str(test_repo_dir), container=container),
        mcp_tools.search_repository_code_tool(str(test_repo_dir), query="User", container=container),
        mcp_tools.search_repository_code_tool(str(test_repo_dir), query="AuthService", container=container),
        mcp_tools.list_indexed_repositories_tool(container=container),
    ]

    results = await asyncio.gather(*coros)
    for r in results:
        assert r["success"] is True


@pytest.mark.asyncio
async def test_mcp_full_jsonrpc_protocol_session(test_repo_dir: Path):
    """Exercise real MCP JSON-RPC protocol communication via ClientSession and memory streams."""
    container = await get_test_container(test_repo_dir)
    server = create_mcp_server(container=container)

    async with create_client_server_memory_streams() as (client_streams, server_streams):
        async with anyio.create_task_group() as tg:
            # Launch server on server memory stream
            tg.start_soon(
                server._lowlevel_server.run,
                server_streams[0],
                server_streams[1],
                server._lowlevel_server.create_initialization_options(),
            )

            # Connect client on client memory stream
            async with ClientSession(client_streams[0], client_streams[1]) as session:
                await session.initialize()

                # 1. Discover tools over protocol
                tools_res = await session.list_tools()
                tool_names = [t.name for t in tools_res.tools]
                assert "get_agent_context" in tool_names
                assert "get_repository_summary" in tool_names
                assert "get_ast_call_graph" in tool_names
                assert "search_repository_code" in tool_names
                assert "list_indexed_repositories" in tool_names

                # 2. Execute get_repository_summary tool over protocol
                call_res = await session.call_tool(
                    "get_repository_summary",
                    {"repository_path": str(test_repo_dir)},
                )
                assert not call_res.is_error
                assert len(call_res.content) > 0
                text_content = call_res.content[0].text
                assert "sample_repo" in text_content or "Python" in text_content

                # 3. Execute search_repository_code tool over protocol
                search_res = await session.call_tool(
                    "search_repository_code",
                    {"repository_path": str(test_repo_dir), "query": "AuthService"},
                )
                assert not search_res.is_error
                assert "auth.py" in search_res.content[0].text or "AuthService" in search_res.content[0].text

                # Shutdown
                tg.cancel_scope.cancel()
