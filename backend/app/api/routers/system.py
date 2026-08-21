"""System and health API router.

Exposes system diagnostics, health checks, dashboard metrics, and LLM provider hot-reloading.
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.schemas import ErrorResponse
from app.application.container import get_container
from app.application.use_cases.memory import MemoryUseCases
from app.application.use_cases.system import SystemUseCases

router = APIRouter(tags=["system"])


def get_system_use_cases() -> SystemUseCases:
    return get_container().get_system_use_cases()


def get_memory_use_cases() -> MemoryUseCases:
    return get_container().get_memory_use_cases()


class UpdateProviderRequest(BaseModel):
    provider: str
    base_url: str
    model: str
    api_key: str = "local"


@router.get("/health")
async def health_endpoint(
    system_use_cases: SystemUseCases = Depends(get_system_use_cases),
) -> dict[str, Any]:
    """Check system health."""
    result = await system_use_cases.health()
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=503, detail=result.model_dump())
    return result.model_dump()


@router.get("/status")
async def status_endpoint(
    system_use_cases: SystemUseCases = Depends(get_system_use_cases),
) -> dict[str, Any]:
    """Get backend status."""
    result = await system_use_cases.get_backend_status()
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=503, detail=result.model_dump())
    return result.model_dump()


@router.get("/dashboard/stats")
async def dashboard_stats_endpoint(
    memory_use_cases: MemoryUseCases = Depends(get_memory_use_cases),
) -> dict[str, Any]:
    """Get aggregate dashboard statistics."""
    result = await memory_use_cases.get_dashboard_stats()
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result.model_dump()


@router.post("/provider/update")
async def provider_update_endpoint(
    request: UpdateProviderRequest,
    system_use_cases: SystemUseCases = Depends(get_system_use_cases),
) -> dict[str, Any]:
    """Hot-reload the active LLM inference provider without restarting."""
    result = await system_use_cases.update_provider(
        provider=request.provider,
        base_url=request.base_url,
        model=request.model,
        api_key=request.api_key,
    )
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result
