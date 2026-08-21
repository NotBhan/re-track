"""Memory and knowledge graph API router.

Exposes dataset management, dataset ingestion items, dataset deletion (forget),
topology statistics, knowledge graph queries, vector embeddings, and cognification.
"""

from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas import (
    CognifyRequest,
    ErrorResponse,
    ForgetDatasetRequest,
)
from app.application.container import get_container
from app.application.use_cases.memory import MemoryUseCases

router = APIRouter(tags=["memory"])


def get_memory_use_cases() -> MemoryUseCases:
    return get_container().get_memory_use_cases()


@router.get("/datasets")
async def datasets_endpoint(
    memory_use_cases: MemoryUseCases = Depends(get_memory_use_cases),
) -> dict[str, Any]:
    """List all stored datasets."""
    result = await memory_use_cases.list_datasets()
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result.model_dump()


@router.get("/datasets/{dataset_id}/items")
async def dataset_items_endpoint(
    dataset_id: str,
    memory_use_cases: MemoryUseCases = Depends(get_memory_use_cases),
) -> dict[str, Any]:
    """Get stored/ingested files for a dataset."""
    result = await memory_use_cases.get_dataset_items(dataset_id)
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result.model_dump()


@router.post("/forget")
async def forget_endpoint(
    request: ForgetDatasetRequest,
    memory_use_cases: MemoryUseCases = Depends(get_memory_use_cases),
) -> dict[str, Any]:
    """Forget a dataset."""
    result = await memory_use_cases.forget_dataset(request)
    if result is None:
        return {"success": True, "message": "Dataset forgotten successfully"}
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result.model_dump()


@router.get("/memory/stats")
async def memory_stats_endpoint(
    memory_use_cases: MemoryUseCases = Depends(get_memory_use_cases),
) -> dict[str, Any]:
    """Get memory topology statistics."""
    result = await memory_use_cases.get_memory_stats()
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result.model_dump()


@router.get("/memory/graph")
async def memory_graph_endpoint(
    dataset: Optional[str] = None,
    memory_use_cases: MemoryUseCases = Depends(get_memory_use_cases),
) -> dict[str, Any]:
    """Get authoritative Cognee knowledge graph nodes and edges."""
    result = await memory_use_cases.get_memory_graph(dataset_name=dataset)
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result.model_dump()


@router.get("/memory/vectors")
async def memory_vectors_endpoint(
    memory_use_cases: MemoryUseCases = Depends(get_memory_use_cases),
) -> dict[str, Any]:
    """Get authoritative vector space and embedding index details."""
    result = await memory_use_cases.get_memory_vectors()
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result.model_dump()


@router.post("/memory/cognify")
async def memory_cognify_endpoint(
    request: CognifyRequest,
    memory_use_cases: MemoryUseCases = Depends(get_memory_use_cases),
) -> dict[str, Any]:
    """Extract memory vectors in LanceDB and build knowledge graph in Kùzu."""
    result = await memory_use_cases.cognify_dataset(request)
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result.model_dump()
