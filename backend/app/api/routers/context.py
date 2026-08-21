"""Context generation and repository indexing API router.

Exposes indexing orchestration, context package synthesis, and AI agent middleware context generation.
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas import (
    ErrorResponse,
    GenerateContextRequest,
    IndexRepositoryRequest,
)
from app.application.container import get_container
from app.application.use_cases.context import ContextUseCases
from app.application.use_cases.indexing import IndexingUseCases
from app.models.agent_context import AgentContextRequest

router = APIRouter(tags=["context"])


def get_context_use_cases() -> ContextUseCases:
    return get_container().get_context_use_cases()


def get_indexing_use_cases() -> IndexingUseCases:
    return get_container().get_indexing_use_cases()


@router.post("/index")
async def index_endpoint(
    request: IndexRepositoryRequest,
    indexing_use_cases: IndexingUseCases = Depends(get_indexing_use_cases),
) -> dict[str, Any]:
    """Index a repository."""
    result = await indexing_use_cases.index_repository(request)
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result.model_dump()


@router.post("/context")
async def context_endpoint(
    request: GenerateContextRequest,
    context_use_cases: ContextUseCases = Depends(get_context_use_cases),
) -> dict[str, Any]:
    """Generate a Context Package."""
    result = await context_use_cases.generate_context(request)
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result.model_dump()


@router.post("/api/v1/context")
async def agent_context_endpoint(
    request: AgentContextRequest,
    context_use_cases: ContextUseCases = Depends(get_context_use_cases),
) -> dict[str, Any]:
    """Generate an optimized context package for external AI coding agents.

    Parses task intent and code symbols, merges CGC structural call graphs
    with Cognee semantic memory, and applies adaptive budgeting for 8GB VRAM/RAM hardware.
    """
    result = await context_use_cases.get_agent_context(request)
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result.model_dump()
