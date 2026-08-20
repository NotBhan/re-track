"""Context Package persistence use cases for RE:Track.

Coordinates CRUD operations for saved Context Packages.
All dependencies are explicitly injected via constructor capability ports.
"""

from datetime import datetime, timezone
import logging
import time
from typing import Any, Optional
import uuid

from app.application.dto import (
    ContextPackageAppendRequest,
    ContextPackageListResponse,
    ContextPackageResponse,
    ContextPackageSaveRequest,
    ErrorResponse,
)
from app.application.ports.context_package_repository import ContextPackageRepositoryPort
from app.models.context_package import SavedContextPackage

logger = logging.getLogger(__name__)


def _pkg_to_response(pkg: Any) -> ContextPackageResponse:
    """Convert a SavedContextPackage object to a Pydantic response model."""
    return ContextPackageResponse(
        id=getattr(pkg, "id", ""),
        name=getattr(pkg, "name", ""),
        task=getattr(pkg, "task", ""),
        objective=getattr(pkg, "objective", ""),
        repository_id=getattr(pkg, "repository_id", None),
        repository_name=getattr(pkg, "repository_name", None),
        repository_branch=getattr(pkg, "repository_branch", None),
        repository_commit=getattr(pkg, "repository_commit", None),
        indexing_version=getattr(pkg, "indexing_version", "1.0.0"),
        markdown=getattr(pkg, "markdown", ""),
        section_count=getattr(pkg, "section_count", 0),
        token_estimate=getattr(pkg, "token_estimate", 0),
        retrieved_memories=getattr(pkg, "retrieved_memories", 0),
        deduplicated_memories=getattr(pkg, "deduplicated_memories", 0),
        compression_ratio=getattr(pkg, "compression_ratio", 1.0),
        total_time_ms=getattr(pkg, "total_time_ms", 0),
        created_at=getattr(pkg, "created_at", ""),
        updated_at=getattr(pkg, "updated_at", ""),
        tags=getattr(pkg, "tags", []) or [],
    )


class PackageUseCases:
    """Orchestrates Context Package saving, retrieval, deletion, and appending."""

    def __init__(
        self,
        package_repository: Optional[ContextPackageRepositoryPort] = None,
    ) -> None:
        self._repo = package_repository

    async def save_context_package(
        self,
        request: ContextPackageSaveRequest,
    ) -> ContextPackageResponse | ErrorResponse:
        """Save a generated Context Package to persistent storage."""
        start = time.monotonic()
        logger.info("use_case: save_context_package() | name=%s", request.name)

        try:
            if not self._repo:
                raise ValueError("Package repository is not configured")

            now = datetime.now(timezone.utc).isoformat()
            pkg_id = str(uuid.uuid4())

            pkg = SavedContextPackage(
                id=pkg_id,
                name=request.name,
                task=request.task,
                objective=request.objective,
                repository_id=request.repository_id,
                repository_name=request.repository_name,
                repository_branch=request.repository_branch,
                repository_commit=request.repository_commit,
                indexing_version=request.indexing_version,
                markdown=request.markdown,
                section_count=request.section_count,
                token_estimate=request.token_estimate,
                retrieved_memories=request.retrieved_memories,
                deduplicated_memories=request.deduplicated_memories,
                compression_ratio=request.compression_ratio,
                total_time_ms=int(request.total_time_ms),
                created_at=now,
                updated_at=now,
                tags=request.tags,
            )

            res = self._repo.save(pkg)
            saved = await res if hasattr(res, "__await__") else res
            elapsed = time.monotonic() - start
            logger.info("use_case: save_context_package() complete | id=%s | %.2fs", getattr(saved, "id", ""), elapsed)
            return _pkg_to_response(saved)
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: save_context_package() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(
                error=type(e).__name__,
                message=f"Failed to save context package: {e}",
            )

    async def list_context_packages(self) -> ContextPackageListResponse | ErrorResponse:
        """List all saved context packages."""
        start = time.monotonic()
        logger.info("use_case: list_context_packages()")

        try:
            if not self._repo:
                return ContextPackageListResponse(success=True, packages=[], total_count=0)

            res = self._repo.list_all()
            packages = await res if hasattr(res, "__await__") else res
            responses = [_pkg_to_response(p) for p in packages]
            elapsed = time.monotonic() - start
            logger.info("use_case: list_context_packages() complete | count=%d | %.2fs", len(responses), elapsed)
            return ContextPackageListResponse(
                success=True,
                packages=responses,
                total_count=len(responses),
            )
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: list_context_packages() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(
                error=type(e).__name__,
                message=f"Failed to list context packages: {e}",
            )

    async def get_context_package(self, package_id: str) -> ContextPackageResponse | ErrorResponse:
        """Get a single saved context package by ID."""
        start = time.monotonic()
        logger.info("use_case: get_context_package() | id=%s", package_id)

        try:
            if not self._repo:
                return ErrorResponse(error="NotFoundError", message=f"Context package {package_id} not found")

            res = self._repo.get(package_id)
            pkg = await res if hasattr(res, "__await__") else res
            if not pkg:
                return ErrorResponse(
                    error="NotFoundError",
                    message=f"Context package {package_id} not found",
                )
            elapsed = time.monotonic() - start
            logger.info("use_case: get_context_package() complete | id=%s | %.2fs", package_id, elapsed)
            return _pkg_to_response(pkg)
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: get_context_package() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(
                error=type(e).__name__,
                message=f"Failed to get context package: {e}",
            )

    async def delete_context_package(self, package_id: str) -> dict | ErrorResponse:
        """Delete a saved context package by ID."""
        start = time.monotonic()
        logger.info("use_case: delete_context_package() | id=%s", package_id)

        try:
            if not self._repo:
                return ErrorResponse(error="NotFoundError", message=f"Context package {package_id} not found")

            res = self._repo.delete(package_id)
            deleted = await res if hasattr(res, "__await__") else res
            if not deleted:
                return ErrorResponse(
                    error="NotFoundError",
                    message=f"Context package {package_id} not found",
                )
            elapsed = time.monotonic() - start
            logger.info("use_case: delete_context_package() complete | id=%s | %.2fs", package_id, elapsed)
            return {"success": True, "message": f"Context package {package_id} deleted"}
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: delete_context_package() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(
                error=type(e).__name__,
                message=f"Failed to delete context package: {e}",
            )

    async def append_context_package(
        self,
        package_id: str,
        request: ContextPackageAppendRequest,
    ) -> ContextPackageResponse | ErrorResponse:
        """Append an iterative task/query and additional context to an existing package."""
        start = time.monotonic()
        logger.info("use_case: append_context_package() | id=%s", package_id)

        try:
            if not self._repo:
                return ErrorResponse(error="NotFoundError", message=f"Context package {package_id} not found")

            res = self._repo.append(
                package_id=package_id,
                additional_task=request.additional_task,
                additional_markdown=request.additional_markdown,
                additional_objective=request.additional_objective or "",
            )
            updated = await res if hasattr(res, "__await__") else res
            if not updated:
                return ErrorResponse(
                    error="NotFoundError",
                    message=f"Context package {package_id} not found",
                )
            elapsed = time.monotonic() - start
            logger.info("use_case: append_context_package() complete | id=%s | %.2fs", package_id, elapsed)
            return _pkg_to_response(updated)
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: append_context_package() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(
                error=type(e).__name__,
                message=f"Failed to append to context package: {e}",
            )
