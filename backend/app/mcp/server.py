"""RE:Track Model Context Protocol (MCP) Server.

Inbound driving adapter providing an MCP stdio server interface for external AI coding agents.
Wires MCP protocol requests to Application Use Cases via ApplicationContainer.
"""

import asyncio
import logging
from pathlib import Path
import sys
from typing import Any, Optional

from mcp.server import MCPServer

from app import __version__
from app.application.container import ApplicationContainer, get_container
from app.mcp import tools as mcp_tools

logger = logging.getLogger(__name__)


def create_mcp_server(container: Optional[ApplicationContainer] = None) -> MCPServer:
    """Create and configure an MCPServer instance with all RE:Track tools registered.

    Args:
        container: Optional explicit ApplicationContainer (defaults to composition root container).
    """
    server = MCPServer(
        name="retrack-mcp",
        version=__version__,
        instructions=(
            "RE:Track (RefinedEngine Track) MCP server providing persistent repository memory, "
            "deterministic AST call graphs, architectural summaries, and high-precision context packages "
            "for AI coding agents."
        ),
    )

    # Tool 1: get_agent_context
    @server.tool(
        name="get_agent_context",
        description=(
            "Synthesizes a high-precision, token-budgeted Context Package for a coding task in a repository, "
            "including AST call graphs, caller/callee relationships, symbol references, and relevant source snippets."
        ),
    )
    async def get_agent_context(
        task_prompt: str,
        repository_path: str,
        max_tokens: int = 8000,
        dataset_name: Optional[str] = None,
        include_structural_graph: bool = True,
    ) -> dict[str, Any]:
        """Synthesize a high-precision, token-budgeted Context Package for a coding task.

        Args:
            task_prompt: Developer task, query, or bug description to solve.
            repository_path: Absolute or relative path to the target local repository.
            max_tokens: Target token budget for the context package (default: 8000).
            dataset_name: Optional logical memory dataset name (defaults to repository folder name).
            include_structural_graph: Whether to include AST call graph and dependency trees (default: true).
        """
        return await mcp_tools.get_agent_context_tool(
            task_prompt=task_prompt,
            repository_path=repository_path,
            max_tokens=max_tokens,
            dataset_name=dataset_name,
            include_structural_graph=include_structural_graph,
            container=container,
        )

    # Tool 2: get_repository_summary
    @server.tool(
        name="get_repository_summary",
        description=(
            "Returns high-level structural knowledge of a repository: purpose, technology stack, "
            "architectural layers, key components, and entry points."
        ),
    )
    async def get_repository_summary(
        repository_path: str,
    ) -> dict[str, Any]:
        """Retrieve high-level architectural knowledge and tech stack for a repository.

        Args:
            repository_path: Absolute or relative path to the target local repository.
        """
        return await mcp_tools.get_repository_summary_tool(
            repository_path=repository_path,
            container=container,
        )

    # Tool 3: get_ast_call_graph
    @server.tool(
        name="get_ast_call_graph",
        description=(
            "Returns the deterministic AST call graph (nodes and caller/callee directed edges) "
            "extracted from repository code."
        ),
    )
    async def get_ast_call_graph(
        repository_path: str,
        file_filter: Optional[str] = None,
        max_nodes: int = 150,
    ) -> dict[str, Any]:
        """Extract deterministic AST call graph (nodes and directed edges).

        Args:
            repository_path: Absolute or relative path to the target local repository.
            file_filter: Optional path prefix to filter graph nodes (e.g., 'backend/app/services').
            max_nodes: Maximum nodes to return (default: 150, max: 500).
        """
        return await mcp_tools.get_ast_call_graph_tool(
            repository_path=repository_path,
            file_filter=file_filter,
            max_nodes=max_nodes,
            container=container,
        )

    # Tool 4: search_repository_code
    @server.tool(
        name="search_repository_code",
        description=(
            "Searches repository source files for matching symbols, function definitions, classes, "
            "and keyword references with relevance ranking."
        ),
    )
    async def search_repository_code(
        repository_path: str,
        query: str,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Search repository code for matching symbols, function names, and keywords.

        Args:
            repository_path: Absolute or relative path to the target local repository.
            query: Symbol name, function name, class name, or keyword query to search.
            limit: Maximum number of candidate files to return (default: 10).
        """
        return await mcp_tools.search_repository_code_tool(
            repository_path=repository_path,
            query=query,
            limit=limit,
            container=container,
        )

    # Tool 5: list_indexed_repositories
    @server.tool(
        name="list_indexed_repositories",
        description=(
            "Lists all repositories registered in RE:Track with their metadata, local paths, "
            "detected languages, and indexing status."
        ),
    )
    async def list_indexed_repositories() -> dict[str, Any]:
        """List all repositories registered in RE:Track with metadata and status."""
        return await mcp_tools.list_indexed_repositories_tool(
            container=container,
        )

    return server


async def run_mcp_stdio(container: Optional[ApplicationContainer] = None) -> None:
    """Run the RE:Track MCP server over stdio transport."""
    from app.core.logging import setup_logging
    setup_logging(level=logging.INFO, stream=sys.stderr)

    app_container = container or get_container()
    server = create_mcp_server(container=app_container)
    logger.info("Starting RE:Track MCP stdio server...")
    try:
        await server.run_stdio_async()
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("MCP stdio server shutting down gracefully...")
    except Exception as e:
        logger.error("MCP stdio server encountered fatal error: %s", e, exc_info=True)
        raise


def main() -> None:
    """Run MCP stdio server entry point."""
    from app.core.logging import setup_logging
    setup_logging(stream=sys.stderr)
    try:
        asyncio.run(run_mcp_stdio())
    except (KeyboardInterrupt, asyncio.CancelledError):
        sys.exit(0)
    except Exception as e:
        sys.stderr.write(f"[RE:Track MCP Fatal] {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()

