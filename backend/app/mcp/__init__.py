"""RE:Track Model Context Protocol (MCP) Inbound Adapter Package.

Exposes RE:Track context synthesis and repository knowledge capabilities
to external AI coding agents via MCP stdio/SSE protocol.
"""

from app.mcp.server import create_mcp_server, run_mcp_stdio
from app.mcp.tools import (
    get_agent_context_tool,
    get_ast_call_graph_tool,
    get_repository_summary_tool,
    list_indexed_repositories_tool,
    search_repository_code_tool,
)

__all__ = [
    "create_mcp_server",
    "run_mcp_stdio",
    "get_agent_context_tool",
    "get_repository_summary_tool",
    "get_ast_call_graph_tool",
    "search_repository_code_tool",
    "list_indexed_repositories_tool",
]
