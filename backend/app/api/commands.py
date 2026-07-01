"""Async API commands for AndesContext.

Thin command layer that validates input, delegates to services,
and returns serializable responses. No business logic lives here.

Every command:
- Validates request parameters
- Logs the request with timing
- Delegates to the appropriate service
- Returns a Pydantic response model
- Catches and wraps errors in ErrorResponse
"""

import logging
import time
from pathlib import Path
from typing import Optional

from app.api.schemas import (
    BackendStatusResponse,
    ContextResponse,
    DatasetInfo,
    DatasetListResponse,
    ErrorResponse,
    ForgetDatasetRequest,
    GenerateContextRequest,
    HealthResponse,
    IndexRepositoryRequest,
    IndexRepositoryResponse,
)
from app.config.settings import Settings, get_settings
from app.models.errors import AndesContextError, CogneeServiceError
from app.services.context_service import ContextService
from app.services.cognee_service import CogneeService
from app.services.indexing_service import IndexingService

logger = logging.getLogger(__name__)

# Backend version
VERSION = "0.1.0"


# --- Service singletons (lazy-initialized) ---

_cognee_service: Optional[CogneeService] = None
_indexing_service: Optional[IndexingService] = None
_context_service: Optional[ContextService] = None
_settings: Optional[Settings] = None


def _ensure_services() -> None:
    """Raise if any service is not initialized."""
    if _cognee_service is None or _indexing_service is None or _context_service is None:
        raise CogneeServiceError(
            "Backend services not initialized. Call initialize_backend() first."
        )


async def initialize_backend(settings: Optional[Settings] = None) -> None:
    """Initialize all backend services.

    Args:
        settings: Optional settings override. Uses default if None.
    """
    global _cognee_service, _indexing_service, _context_service, _settings

    _settings = settings or get_settings()
    _cognee_service = CogneeService(_settings)
    await _cognee_service.initialize()

    _indexing_service = IndexingService(_cognee_service)
    _context_service = ContextService(_cognee_service)

    logger.info("Backend services initialized")


# --- Commands ---


async def health() -> HealthResponse | ErrorResponse:
    """Check system health: Cognee, Ollama, and storage."""
    start = time.monotonic()
    logger.info("command: health()")

    try:
        settings = _settings or get_settings()
        cognee = _cognee_service

        ollama_reachable = settings.ollama.check_connection()
        cognee_ok = cognee is not None and cognee.is_initialized

        status = "ok" if (ollama_reachable and cognee_ok) else "degraded"

        response = HealthResponse(
            status=status,
            ollama_reachable=ollama_reachable,
            cognee_initialized=cognee_ok,
            version=VERSION,
        )

        elapsed = time.monotonic() - start
        logger.info("command: health() | status=%s | %.2fs", response.status, elapsed)
        return response

    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error("command: health() failed | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=f"Health check failed: {e}",
        )


async def list_datasets() -> DatasetListResponse | ErrorResponse:
    """List all datasets stored in Cognee memory.

    Returns an empty list gracefully if Cognee is not initialized.
    """
    start = time.monotonic()
    logger.info("command: list_datasets()")

    try:
        cognee = _cognee_service
        if cognee is None or not cognee.is_initialized:
            logger.info("command: list_datasets() | cognee not initialized, returning empty")
            return DatasetListResponse(success=True, datasets=[], total_count=0)

        raw_datasets = await cognee.list_datasets()

        datasets = [
            DatasetInfo(
                id=ds["id"],
                name=ds["name"],
                created_at=ds["created_at"],
                file_count=ds["file_count"],
            )
            for ds in raw_datasets
        ]

        response = DatasetListResponse(
            success=True,
            datasets=datasets,
            total_count=len(datasets),
        )

        elapsed = time.monotonic() - start
        logger.info(
            "command: list_datasets() complete | count=%d | %.2fs",
            len(datasets),
            elapsed,
        )
        return response

    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error("command: list_datasets() failed | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=f"Failed to list datasets: {e}",
        )


async def get_backend_status() -> BackendStatusResponse | ErrorResponse:
    """Return detailed backend status including configuration and datasets."""
    start = time.monotonic()
    logger.info("command: get_backend_status()")

    try:
        settings = _settings or get_settings()
        cognee = _cognee_service

        ollama_reachable = settings.ollama.check_connection()
        cognee_ok = cognee is not None and cognee.is_initialized
        status = "ok" if (ollama_reachable and cognee_ok) else "degraded"

        response = BackendStatusResponse(
            status=status,
            ollama_reachable=ollama_reachable,
            ollama_host=settings.ollama.host,
            ollama_port=settings.ollama.port,
            llm_model=settings.ollama.llm_model,
            embedding_model=settings.ollama.embedding_model,
            vector_db=settings.storage.vector_db,
            graph_db=settings.storage.graph_db,
            relational_db=settings.storage.relational_db,
            data_root=str(settings.storage.data_root),
            system_root=str(settings.storage.system_root),
            cognee_initialized=cognee_ok,
        )

        elapsed = time.monotonic() - start
        logger.info("command: get_backend_status() complete | %.2fs", elapsed)
        return response

    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error("command: get_backend_status() failed | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=f"Status check failed: {e}",
        )


async def index_repository(
    request: IndexRepositoryRequest,
) -> IndexRepositoryResponse | ErrorResponse:
    """Index a repository into Cognee memory.

    Validates the repository path exists and is a directory,
    then delegates to IndexingService.
    """
    start = time.monotonic()
    logger.info(
        "command: index_repository() | repo=%s | dataset=%s",
        request.repository_path,
        request.dataset_name,
    )

    try:
        _ensure_services()

        repo_path = Path(request.repository_path).resolve()
        if not repo_path.exists():
            raise ValueError(f"Repository path does not exist: {request.repository_path}")
        if not repo_path.is_dir():
            raise ValueError(f"Path is not a directory: {request.repository_path}")

        progress = await _indexing_service.index_repository(
            repo_path=repo_path,
            dataset_name=request.dataset_name,
        )

        response = IndexRepositoryResponse(
            success=progress.failed_files == 0,
            repository_path=str(repo_path),
            dataset_name=request.dataset_name,
            total_files=progress.total_files,
            processed_files=progress.processed_files,
            failed_files=progress.failed_files,
            total_batches=progress.total_batches,
            failed_paths=progress.failed_paths,
            summary=progress.summary(),
        )

        elapsed = time.monotonic() - start
        logger.info(
            "command: index_repository() complete | files=%d | %.2fs",
            progress.processed_files,
            elapsed,
        )
        return response

    except ValueError as e:
        elapsed = time.monotonic() - start
        logger.error("command: index_repository() validation error | %.2fs | %s", elapsed, e)
        raise
    except CogneeServiceError as e:
        elapsed = time.monotonic() - start
        logger.error("command: index_repository() service error | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=f"Indexing failed: {e}",
        )
    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error("command: index_repository() failed | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=f"Indexing failed: {e}",
        )


async def generate_context(
    request: GenerateContextRequest,
) -> ContextResponse | ErrorResponse:
    """Generate a Context Package for a developer task.

    Validates query is non-empty, datasets are provided,
    then delegates to ContextService.
    """
    start = time.monotonic()
    logger.info(
        "command: generate_context() | task=%s | datasets=%s | top_k=%d",
        request.task[:80],
        request.datasets,
        request.top_k,
    )

    try:
        _ensure_services()

        if not request.task.strip():
            raise ValueError("Task must not be empty")
        if not request.datasets:
            raise ValueError("at least one dataset must be provided")

        package = await _context_service.generate_context_package(
            task=request.task,
            datasets=request.datasets,
            top_k=request.top_k,
        )

        response = ContextResponse(
            success=True,
            task=package.task,
            objective=package.objective,
            markdown=package.markdown,
            section_count=package.section_count,
            source_count=package.source_count,
            token_estimate=package.token_estimate,
            dataset=package.dataset,
            retrieved_memories=package.metadata.retrieved_memory_count if package.metadata else 0,
            deduplicated_memories=package.metadata.deduplicated_count if package.metadata else 0,
            compressed_memories=package.metadata.compressed_count if package.metadata else 0,
            compression_ratio=package.metadata.compression_ratio if package.metadata else 1.0,
            retrieval_time_ms=package.metadata.retrieval_time_ms if package.metadata else 0,
            total_time_ms=package.metadata.total_time_ms if package.metadata else 0,
            reference_count=len(package.references),
            section_headings=[s.heading for s in package.sections],
        )

        elapsed = time.monotonic() - start
        logger.info(
            "command: generate_context() complete | sources=%d | ~%d tokens | %.2fs",
            package.source_count,
            package.token_estimate,
            elapsed,
        )
        return response

    except ValueError as e:
        elapsed = time.monotonic() - start
        logger.error("command: generate_context() validation error | %.2fs | %s", elapsed, e)
        raise
    except CogneeServiceError as e:
        elapsed = time.monotonic() - start
        logger.error("command: generate_context() service error | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=f"Context generation failed: {e}",
        )
    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error("command: generate_context() failed | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=f"Context generation failed: {e}",
        )


async def forget_dataset(
    request: ForgetDatasetRequest,
) -> None | ErrorResponse:
    """Forget (delete) a dataset or specific data item from Cognee memory.

    Validates that at least one identifier is provided,
    then delegates to CogneeService.

    Returns None on success, ErrorResponse on failure.
    """
    start = time.monotonic()
    logger.info(
        "command: forget_dataset() | dataset=%s | dataset_id=%s | data_id=%s",
        request.dataset,
        request.dataset_id,
        request.data_id,
    )

    try:
        _ensure_services()

        if not any([request.dataset, request.dataset_id, request.data_id]):
            raise ValueError("At least one of dataset, dataset_id, or data_id must be provided")

        await _cognee_service.forget(
            dataset=request.dataset,
            dataset_id=request.dataset_id,
            data_id=request.data_id,
        )

        elapsed = time.monotonic() - start
        logger.info("command: forget_dataset() complete | %.2fs", elapsed)
        return None

    except ValueError as e:
        elapsed = time.monotonic() - start
        logger.error("command: forget_dataset() validation error | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=str(e),
        )
    except CogneeServiceError as e:
        elapsed = time.monotonic() - start
        logger.error("command: forget_dataset() service error | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=f"Forget operation failed: {e}",
        )
    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error("command: forget_dataset() failed | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=f"Forget operation failed: {e}",
        )
