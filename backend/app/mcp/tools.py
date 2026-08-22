"""MCP Tool implementations for RE:Track.

Inbound driving adapter that maps MCP tool requests to Application Use Cases.
Contains zero retrieval, ranking, persistence, or business logic.
Delegates strictly to ContextUseCases, RepositoryUseCases, and IndexingUseCases.
"""

import logging
from pathlib import Path
import sys
from typing import Any, Optional

from app.application.container import ApplicationContainer, get_container
from app.application.dto import (
    AgentContextRequest,
    AgentContextResponse,
    ASTCallGraphResponse,
    ErrorResponse,
    RepositoryListResponse,
    RepositorySummaryResponse,
    SourceSearchResponse,
)

logger = logging.getLogger(__name__)


def _resolve_and_validate_repo_path(
    repository_path: str,
    container: Optional[ApplicationContainer] = None,
) -> tuple[Optional[Path], Optional[str], Optional[str]]:
    """Resolve and validate that a repository path exists, is authorized, is a directory, and is safe.

    Returns:
        (resolved_path, error_type, error_message)
    """
    if not repository_path or not repository_path.strip():
        return None, "ValidationError", "Repository path must not be empty"

    try:
        resolved = Path(repository_path).resolve()
    except Exception as e:
        return None, "ValidationError", f"Invalid path syntax: {e}"

    if not resolved.exists():
        return None, "ValidationError", f"Repository path does not exist: {repository_path}"

    if not resolved.is_dir():
        return None, "ValidationError", f"Repository path is not a directory: {repository_path}"

    # Prevent root directory scans
    if str(resolved) in ("/", "\\", "C:\\", "C:/"):
        return None, "ValidationError", "Scanning the filesystem root directory is prohibited"

    # Verify authorization against WorkspaceAuthorizationPort if container is available
    c = container or get_container()
    if c and hasattr(c, "workspace_auth") and c.workspace_auth:
        is_auth, reason = c.workspace_auth.is_path_authorized(str(resolved))
        if not is_auth:
            return None, "AuthorizationError", reason or f"Access denied to unauthorized repository path: {repository_path}"

    return resolved, None, None


async def get_agent_context_tool(
    task_prompt: str,
    repository_path: str,
    max_tokens: int = 8000,
    dataset_name: Optional[str] = None,
    include_structural_graph: bool = True,
    container: Optional[ApplicationContainer] = None,
) -> dict[str, Any]:
    """Synthesize a high-precision, token-budgeted Context Package for a coding task.

    Args:
        task_prompt: Developer task, query, or bug description to solve.
        repository_path: Absolute or relative path to the target local repository.
        max_tokens: Target token budget for the context package (default: 8000).
        dataset_name: Optional logical memory dataset name (defaults to repository folder name).
        include_structural_graph: Whether to include AST call graph and dependency trees (default: true).
        container: Optional explicit ApplicationContainer (defaults to composition root container).
    """
    try:
        c = container or get_container()
        repo_path, err_type, err_msg = _resolve_and_validate_repo_path(repository_path, c)
        if err_type or repo_path is None:
            return {"success": False, "error": err_type, "message": err_msg}

        if not task_prompt or not task_prompt.strip():
            return {"success": False, "error": "ValidationError", "message": "task_prompt must not be empty"}

        context_uc = c.get_context_use_cases()

        request = AgentContextRequest(
            task_prompt=task_prompt,
            repository_path=str(repo_path),
            dataset_name=dataset_name,
            max_tokens=max(100, min(32000, max_tokens)),
            include_structural_graph=include_structural_graph,
        )

        result = await context_uc.get_agent_context(request)
        if isinstance(result, ErrorResponse):
            return {"success": False, "error": result.error, "message": result.message}

        if isinstance(result, AgentContextResponse):
            return {
                "success": result.success,
                "context_markdown": result.context_markdown,
                "task_summary": result.task_summary,
                "intent_category": result.intent_category,
                "extracted_symbols": result.extracted_symbols,
                "callers": result.callers,
                "callees": result.callees,
                "related_files": result.related_files,
                "estimated_tokens": result.estimated_tokens,
                "total_time_ms": result.total_time_ms,
            }

        return {"success": False, "error": "UnexpectedResponse", "message": "Unexpected response type from use case"}
    except Exception as e:
        logger.error("get_agent_context_tool internal error: %s", e, exc_info=True)
        sys.stderr.write(f"[RE:Track MCP Error] get_agent_context_tool failed: {e}\n")
        return {
            "success": False,
            "error": "InternalError",
            "message": "An internal error occurred during context synthesis. Check server logs for details.",
        }


async def get_repository_summary_tool(
    repository_path: str,
    container: Optional[ApplicationContainer] = None,
) -> dict[str, Any]:
    """Retrieve high-level architectural knowledge and tech stack for a repository.

    Args:
        repository_path: Absolute or relative path to the target local repository.
        container: Optional explicit ApplicationContainer (defaults to composition root container).
    """
    try:
        c = container or get_container()
        repo_path, err_type, err_msg = _resolve_and_validate_repo_path(repository_path, c)
        if err_type or repo_path is None:
            return {"success": False, "error": err_type, "message": err_msg}

        repo_uc = c.get_repository_use_cases()

        result = await repo_uc.get_repository_summary(str(repo_path))
        if isinstance(result, ErrorResponse):
            return {"success": False, "error": result.error, "message": result.message}

        if isinstance(result, RepositorySummaryResponse):
            return {
                "success": result.success,
                "repository_path": result.repository_path,
                "project_purpose": result.project_purpose,
                "languages": result.languages,
                "frameworks": result.frameworks,
                "databases": result.databases,
                "dependencies": result.dependencies,
                "architecture_pattern": result.architecture_pattern,
                "architecture_layers": result.architecture_layers,
                "key_components": result.key_components,
                "entry_points": result.entry_points,
                "public_apis": result.public_apis,
                "coding_conventions": result.coding_conventions,
                "file_count": result.file_count,
                "call_graph_status": result.call_graph_status,
            }

        return {"success": False, "error": "UnexpectedResponse", "message": "Unexpected response type from use case"}
    except Exception as e:
        logger.error("get_repository_summary_tool internal error: %s", e, exc_info=True)
        sys.stderr.write(f"[RE:Track MCP Error] get_repository_summary_tool failed: {e}\n")
        return {
            "success": False,
            "error": "InternalError",
            "message": "An internal error occurred during summary generation. Check server logs for details.",
        }


async def get_ast_call_graph_tool(
    repository_path: str,
    file_filter: Optional[str] = None,
    max_nodes: int = 150,
    container: Optional[ApplicationContainer] = None,
) -> dict[str, Any]:
    """Extract deterministic AST call graph (caller/callee directed edges and nodes).

    Args:
        repository_path: Absolute or relative path to the target local repository.
        file_filter: Optional path prefix to filter graph nodes (e.g., 'backend/app/services').
        max_nodes: Maximum nodes to return (default: 150, max: 500).
        container: Optional explicit ApplicationContainer (defaults to composition root container).
    """
    try:
        c = container or get_container()
        repo_path, err_type, err_msg = _resolve_and_validate_repo_path(repository_path, c)
        if err_type or repo_path is None:
            return {"success": False, "error": err_type, "message": err_msg}

        repo_uc = c.get_repository_use_cases()

        result = await repo_uc.get_ast_call_graph(
            repository_path=str(repo_path),
            file_filter=file_filter,
            max_nodes=max(1, min(500, max_nodes)),
        )
        if isinstance(result, ErrorResponse):
            return {"success": False, "error": result.error, "message": result.message}

        if isinstance(result, ASTCallGraphResponse):
            return {
                "success": result.success,
                "repository_path": result.repository_path,
                "nodes": result.nodes,
                "edges": result.edges,
                "total_nodes": result.total_nodes,
                "total_edges": result.total_edges,
                "call_graph_status": result.call_graph_status,
                "call_graph_error": result.call_graph_error,
            }

        return {"success": False, "error": "UnexpectedResponse", "message": "Unexpected response type from use case"}
    except Exception as e:
        logger.error("get_ast_call_graph_tool internal error: %s", e, exc_info=True)
        sys.stderr.write(f"[RE:Track MCP Error] get_ast_call_graph_tool failed: {e}\n")
        return {
            "success": False,
            "error": "InternalError",
            "message": "An internal error occurred during AST call graph generation. Check server logs for details.",
        }


async def search_repository_code_tool(
    repository_path: str,
    query: str,
    limit: int = 10,
    container: Optional[ApplicationContainer] = None,
) -> dict[str, Any]:
    """Search repository code for matching symbols, function names, and keywords.

    Args:
        repository_path: Absolute or relative path to the target local repository.
        query: Symbol name, function name, class name, or keyword query to search.
        limit: Maximum number of candidate files to return (default: 10).
        container: Optional explicit ApplicationContainer (defaults to composition root container).
    """
    try:
        c = container or get_container()
        repo_path, err_type, err_msg = _resolve_and_validate_repo_path(repository_path, c)
        if err_type or repo_path is None:
            return {"success": False, "error": err_type, "message": err_msg}

        if not query or not query.strip():
            return {"success": False, "error": "ValidationError", "message": "query must not be empty"}

        context_uc = c.get_context_use_cases()

        result = await context_uc.search_repository_code(
            repository_path=str(repo_path),
            query=query,
            limit=max(1, min(50, limit)),
        )
        if isinstance(result, ErrorResponse):
            return {"success": False, "error": result.error, "message": result.message}

        if isinstance(result, SourceSearchResponse):
            return {
                "success": result.success,
                "repository_path": result.repository_path,
                "query": result.query,
                "results": [
                    {
                        "file_path": r.file_path,
                        "score": r.score,
                        "matched_symbols": r.matched_symbols,
                        "snippet": r.snippet,
                    }
                    for r in result.results
                ],
                "total_results": result.total_results,
            }

        return {"success": False, "error": "UnexpectedResponse", "message": "Unexpected response type from use case"}
    except Exception as e:
        logger.error("search_repository_code_tool internal error: %s", e, exc_info=True)
        sys.stderr.write(f"[RE:Track MCP Error] search_repository_code_tool failed: {e}\n")
        return {
            "success": False,
            "error": "InternalError",
            "message": "An internal error occurred during code search. Check server logs for details.",
        }


async def list_indexed_repositories_tool(
    container: Optional[ApplicationContainer] = None,
) -> dict[str, Any]:
    """List all repositories registered in RE:Track with metadata and status.

    Args:
        container: Optional explicit ApplicationContainer (defaults to composition root container).
    """
    try:
        c = container or get_container()
        repo_uc = c.get_repository_use_cases()

        result = await repo_uc.list_repositories()
        if isinstance(result, ErrorResponse):
            return {"success": False, "error": result.error, "message": result.message}

        if isinstance(result, RepositoryListResponse):
            return {
                "success": result.success,
                "repositories": [
                    {
                        "id": r.id,
                        "name": r.name,
                        "local_path": r.local_path,
                        "status": r.status,
                        "languages": r.languages,
                        "frameworks": r.frameworks,
                        "file_count": r.file_count,
                        "indexed_at": r.indexed_at,
                        "summary": r.summary,
                        "architecture": r.architecture,
                        "components": r.components,
                        "call_graph_status": r.call_graph_status,
                    }
                    for r in result.repositories
                ],
                "total_count": result.total_count,
            }

        return {"success": False, "error": "UnexpectedResponse", "message": "Unexpected response type from use case"}
    except Exception as e:
        logger.error("list_indexed_repositories_tool internal error: %s", e, exc_info=True)
        sys.stderr.write(f"[RE:Track MCP Error] list_indexed_repositories_tool failed: {e}\n")
        return {
            "success": False,
            "error": "InternalError",
            "message": "An internal error occurred while listing repositories. Check server logs for details.",
        }
