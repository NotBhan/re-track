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
