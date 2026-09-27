"""Application and Cognee settings API router.

Exposes persistent configuration retrieval and Cognee parameters update.
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas import CogneeSettingsRequest, ErrorResponse
from app.application.container import get_container
from app.application.use_cases.system import SystemUseCases

router = APIRouter(tags=["settings"])


def get_system_use_cases() -> SystemUseCases:
    return get_container().get_system_use_cases()


@router.get("/settings")
async def settings_get_endpoint(
    system_use_cases: SystemUseCases = Depends(get_system_use_cases),
) -> dict[str, Any]:
    """Get current persistent application and Cognee settings."""
    result = await system_use_cases.get_app_settings()
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result.model_dump()


@router.post("/settings/cognee")
async def settings_cognee_update_endpoint(
    request: CogneeSettingsRequest,
    system_use_cases: SystemUseCases = Depends(get_system_use_cases),
) -> dict[str, Any]:
    """Update and persist Cognee settings to disk and active runtime."""
    result = await system_use_cases.update_cognee_settings(request)
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result.model_dump()


@router.post("/settings/reset")
async def settings_reset_endpoint(
    system_use_cases: SystemUseCases = Depends(get_system_use_cases),
) -> dict[str, Any]:
    """Restore mutable configuration to the application defaults.

    Configuration only: repositories, context packages, memory, and indexed data
    are untouched. The response is the authoritative read-back of the stored
    settings after the reset, and a failure is reported as one.
    """
    result = await system_use_cases.reset_settings()
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result.model_dump()
