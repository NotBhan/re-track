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


@router.get("/health/detailed")
async def detailed_health_endpoint(
    system_use_cases: SystemUseCases = Depends(get_system_use_cases),
) -> dict[str, Any]:
    """Get detailed operational health and diagnostics state."""
    result = await system_use_cases.get_detailed_health()
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=503, detail=result.model_dump())
    return result.model_dump()


@router.get("/diagnostics")
async def get_diagnostics_endpoint(
    system_use_cases: SystemUseCases = Depends(get_system_use_cases),
) -> dict[str, Any]:
    """Generate and return sanitized operational diagnostics report."""
    result = system_use_cases.export_diagnostics()
    if isinstance(result, dict):
        return result
    return {"status": "ok", "path": str(result)}


@router.post("/diagnostics/export")
async def export_diagnostics_endpoint(
    system_use_cases: SystemUseCases = Depends(get_system_use_cases),
) -> dict[str, Any]:
    """Generate and export sanitized operational diagnostic bundle to disk."""
    result = system_use_cases.export_diagnostics(output_path=None)
    return {"status": "ok", "export_path": str(result)}


@router.get("/logs/recent")
async def get_recent_logs_endpoint(
    limit: int = 50,
    system_use_cases: SystemUseCases = Depends(get_system_use_cases),
) -> dict[str, Any]:
    """Get recent sanitized persistent log records."""
    logs = system_use_cases.get_recent_logs(max_entries=limit)
    return {"status": "ok", "count": len(logs), "logs": logs}


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

