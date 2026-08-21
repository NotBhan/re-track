"""Repository management and summarization API router.

Exposes repository registration, clone inspection, language scanning,
indexing progress, prompt suggestions, and summary catalogs.
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas import ErrorResponse, RepositoryCreateRequest
from app.application.container import get_container
from app.application.use_cases.indexing import IndexingUseCases
from app.application.use_cases.repositories import RepositoryUseCases

router = APIRouter(tags=["repositories"])


def get_repository_use_cases() -> RepositoryUseCases:
    return get_container().get_repository_use_cases()


def get_indexing_use_cases() -> IndexingUseCases:
    return get_container().get_indexing_use_cases()


@router.get("/repos")
async def repos_list_endpoint(
    repo_use_cases: RepositoryUseCases = Depends(get_repository_use_cases),
) -> dict[str, Any]:
    """List all managed repositories."""
    result = await repo_use_cases.list_repositories()
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result.model_dump()


@router.post("/repos")
async def repos_create_endpoint(
    request: RepositoryCreateRequest,
    repo_use_cases: RepositoryUseCases = Depends(get_repository_use_cases),
) -> dict[str, Any]:
    """Create (import) a new repository."""
    result = await repo_use_cases.create_repository(request)
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=400, detail=result.model_dump())
    return result.model_dump()


@router.post("/repos/{repo_id}/scan")
async def repos_scan_endpoint(
    repo_id: str,
    repo_use_cases: RepositoryUseCases = Depends(get_repository_use_cases),
) -> dict[str, Any]:
    """Scan a repository for languages, frameworks, and file stats."""
    result = await repo_use_cases.scan_repository(repo_id)
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=400, detail=result.model_dump())
    return result.model_dump()


@router.get("/repos/{repo_id}/progress")
async def repos_progress_endpoint(
    repo_id: str,
    repo_use_cases: RepositoryUseCases = Depends(get_repository_use_cases),
) -> Any:
    """Get indexing progress for a repository."""
    result = await repo_use_cases.get_repository_progress(repo_id)
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=400, detail=result.model_dump())
    return result


@router.delete("/repos/{repo_id}")
async def repos_delete_endpoint(
    repo_id: str,
    repo_use_cases: RepositoryUseCases = Depends(get_repository_use_cases),
) -> Any:
    """Delete a managed repository."""
    result = await repo_use_cases.delete_repository(repo_id)
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=400, detail=result.model_dump())
    return result


@router.get("/repos/{repo_id}/prompts")
async def get_repo_prompts_endpoint(
    repo_id: str,
    repo_use_cases: RepositoryUseCases = Depends(get_repository_use_cases),
) -> dict[str, Any]:
    """Generate repository-tailored prompt recommendations using local LLM or AST metadata."""
    return await repo_use_cases.generate_suggested_prompts(repo_id)


@router.get("/repositories")
async def repositories_endpoint(
    indexing_use_cases: IndexingUseCases = Depends(get_indexing_use_cases),
) -> dict[str, Any]:
    """List all indexed repositories with metadata."""
    result = await indexing_use_cases.get_repository_summaries()
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result.model_dump()
