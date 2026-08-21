"""Context Package persistence and retrieval API router.

Exposes listing, saving, fetching, appending, and deleting context packages.
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas import (
    ContextPackageAppendRequest,
    ContextPackageSaveRequest,
    ErrorResponse,
)
from app.application.container import get_container
from app.application.use_cases.context_packages import PackageUseCases

router = APIRouter(tags=["packages"])


def get_package_use_cases() -> PackageUseCases:
    return get_container().get_package_use_cases()


@router.get("/packages")
async def packages_list_endpoint(
    package_use_cases: PackageUseCases = Depends(get_package_use_cases),
) -> dict[str, Any]:
    """List all saved context packages."""
    result = await package_use_cases.list_context_packages()
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result.model_dump()


@router.post("/packages")
async def packages_save_endpoint(
    request: ContextPackageSaveRequest,
    package_use_cases: PackageUseCases = Depends(get_package_use_cases),
) -> dict[str, Any]:
    """Save a context package."""
    result = await package_use_cases.save_context_package(request)
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result.model_dump()


@router.get("/packages/{package_id}")
async def packages_get_endpoint(
    package_id: str,
    package_use_cases: PackageUseCases = Depends(get_package_use_cases),
) -> dict[str, Any]:
    """Get a single context package by ID."""
    result = await package_use_cases.get_context_package(package_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Package not found")
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result.model_dump()


@router.delete("/packages/{package_id}")
async def packages_delete_endpoint(
    package_id: str,
    package_use_cases: PackageUseCases = Depends(get_package_use_cases),
) -> Any:
    """Delete a context package."""
    result = await package_use_cases.delete_context_package(package_id)
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result


@router.post("/packages/{package_id}/append")
async def packages_append_endpoint(
    package_id: str,
    request: ContextPackageAppendRequest,
    package_use_cases: PackageUseCases = Depends(get_package_use_cases),
) -> dict[str, Any]:
    """Append content to an existing context package."""
    result = await package_use_cases.append_context_package(package_id, request)
    if result is None:
        raise HTTPException(status_code=404, detail="Package not found")
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result.model_dump()
