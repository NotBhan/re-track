"""Context Package persistence use cases for RE:Track.

Coordinates CRUD operations for saved Context Packages.
All dependencies are explicitly injected via constructor.
"""

from datetime import datetime, timezone
import logging
import time
from typing import Optional
import uuid

from app.api.schemas import (
    ContextPackageAppendRequest,
    ContextPackageListResponse,
    ContextPackageResponse,
    ContextPackageSaveRequest,
    ErrorResponse,
)
from app.models.context_package import SavedContextPackage
from app.services.context_package_repository import ContextPackageRepository, JsonContextPackageRepository

logger = logging.getLogger(__name__)


def _pkg_to_response(pkg: SavedContextPackage) -> ContextPackageResponse:
    """Convert a SavedContextPackage dataclass to a Pydantic response model."""
    return ContextPackageResponse(
        id=pkg.id,
        name=pkg.name,
        task=pkg.task,
        objective=pkg.objective,
        repository_id=pkg.repository_id,
        repository_name=pkg.repository_name,
        repository_branch=pkg.repository_branch,
        repository_commit=pkg.repository_commit,
        indexing_version=pkg.indexing_version,
        markdown=pkg.markdown,
        section_count=pkg.section_count,
        token_estimate=pkg.token_estimate,
        retrieved_memories=pkg.retrieved_memories,
        deduplicated_memories=pkg.deduplicated_memories,
        compression_ratio=pkg.compression_ratio,
        total_time_ms=pkg.total_time_ms,
        created_at=pkg.created_at,
        updated_at=pkg.updated_at,
        tags=pkg.tags,
    )


class PackageUseCases:
    """Orchestrates Context Package saving, retrieval, deletion, and appending."""

    def __init__(
        self,
        package_repository: Optional[ContextPackageRepository] = None,
    ) -> None:
        self._repo = package_repository or JsonContextPackageRepository()

    async def save_context_package(
        self,
        request: ContextPackageSaveRequest,
    ) -> ContextPackageResponse | ErrorResponse:
        """Save a generated Context Package to persistent storage."""
        start = time.monotonic()
        logger.info("use_case: save_context_package() | name=%s", request.name)

        try:
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

            saved = await self._repo.save(pkg)
            elapsed = time.monotonic() - start
            logger.info("use_case: save_context_package() complete | id=%s | %.2fs", saved.id, elapsed)
            return _pkg_to_response(saved)
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: save_context_package() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(
                error=type(e).__name__,
                message=f"Failed to save context package: {e}",
            )

    async def list_context_packages(self) -> ContextPackageListResponse | ErrorResponse:
        """List all saved Context Packages."""
        start = time.monotonic()
        logger.info("use_case: list_context_packages()")

        try:
            packages = await self._repo.list_all()
            response_pkgs = [_pkg_to_response(p) for p in packages]
            elapsed = time.monotonic() - start
            logger.info("use_case: list_context_packages() complete | count=%d | %.2fs", len(packages), elapsed)
            return ContextPackageListResponse(
                success=True,
                packages=response_pkgs,
                total_count=len(response_pkgs),
            )
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: list_context_packages() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(
                error=type(e).__name__,
                message=f"Failed to list context packages: {e}",
            )

    async def get_context_package(self, package_id: str) -> Optional[ContextPackageResponse] | ErrorResponse:
        """Get a single saved Context Package by ID."""
        start = time.monotonic()
        logger.info("use_case: get_context_package() | id=%s", package_id)

        try:
            pkg = await self._repo.get(package_id)
            if not pkg:
                return None
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
        """Delete a saved Context Package."""
        start = time.monotonic()
        logger.info("use_case: delete_context_package() | id=%s", package_id)

        try:
            success = await self._repo.delete(package_id)
            if not success:
                return ErrorResponse(
                    error="NotFoundError",
                    message=f"Package {package_id} not found",
                )
            elapsed = time.monotonic() - start
            logger.info("use_case: delete_context_package() complete | id=%s | %.2fs", package_id, elapsed)
            return {"success": True, "message": f"Package {package_id} deleted"}
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
    ) -> Optional[ContextPackageResponse] | ErrorResponse:
        """Append task/markdown content to an existing saved Context Package."""
        start = time.monotonic()
        logger.info("use_case: append_context_package() | id=%s", package_id)

        try:
            pkg = await self._repo.append(
                package_id=package_id,
                additional_task=request.additional_task,
                additional_markdown=request.additional_markdown,
                additional_objective=request.additional_objective,
            )

            if pkg is None:
                return None

            elapsed = time.monotonic() - start
            logger.info("use_case: append_context_package() complete | id=%s | %.2fs", package_id, elapsed)
            return _pkg_to_response(pkg)
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: append_context_package() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(
                error=type(e).__name__,
                message=f"Failed to append to context package: {e}",
            )
